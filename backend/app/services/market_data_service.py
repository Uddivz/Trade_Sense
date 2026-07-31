import asyncio
import logging
import time
from decimal import Decimal

import yfinance as yf
from cachetools import TTLCache

from app.config import settings

logger = logging.getLogger(__name__)

class MarketDataService:
    _MOCK_PRICES = {
        "TCS": Decimal("3950.00"),
        "INFY": Decimal("1560.50"),
        "RELIANCE": Decimal("2480.00"),
        "HDFCBANK": Decimal("1435.00"),
        "ICICIBANK": Decimal("980.00"),
        "SBIN": Decimal("610.40"),
        "ITC": Decimal("440.00"),
        "BHARTIARTL": Decimal("950.00"),
        "LTIM": Decimal("5200.00"),
        "TATASTEEL": Decimal("132.50"),
    }

    # Local fallback TTLCache: max 512 symbols, auto-expires entries after 1 hour.
    CACHE_TTL_SECONDS = 3600  # 1 hour
    _price_cache: TTLCache = TTLCache(maxsize=512, ttl=CACHE_TTL_SECONDS)

    _redis_client = None
    _redis_available: bool = True
    _last_redis_check: float = 0.0
    _redis_cooldown_seconds: float = 60.0

    @classmethod
    async def _get_redis_client(cls):
        """Lazily initialize Redis client with automatic connection testing and cooldown fallback."""
        if not cls._redis_available:
            now = time.time()
            if now - cls._last_redis_check > cls._redis_cooldown_seconds:
                cls._redis_available = True
                cls._last_redis_check = now
            else:
                return None

        if cls._redis_client is None:
            try:
                import redis.asyncio as aioredis
                cls._redis_client = aioredis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0
                )
                await cls._redis_client.ping()
                logger.info("Connected to Redis successfully for market data caching.")
            except Exception as e:
                logger.warning(
                    "Redis connection failed. Falling back to local in-memory cache.",
                    extra={"error": str(e)}
                )
                cls._redis_client = None
                cls._redis_available = False
                cls._last_redis_check = time.time()
        return cls._redis_client

    @classmethod
    def _fetch_from_yfinance_sync(cls, clean_sym: str) -> Decimal | None:
        """Synchronously fetch data from yfinance. Append .NS for Indian stocks."""
        logger.debug("yfinance fetch started", extra={"symbol": clean_sym})
        try:
            ticker_ns = yf.Ticker(f"{clean_sym}.NS")
            hist_ns = ticker_ns.history(period="1d")
            if not hist_ns.empty:
                price = Decimal(str(hist_ns['Close'].iloc[-1]))
                logger.debug("yfinance price fetched (.NS)", extra={"symbol": clean_sym, "price": float(price)})
                return price

            # Fallback without .NS
            ticker = yf.Ticker(clean_sym)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = Decimal(str(hist['Close'].iloc[-1]))
                logger.debug("yfinance price fetched (no suffix)", extra={"symbol": clean_sym, "price": float(price)})
                return price
        except Exception as exc:
            logger.warning(
                "yfinance fetch raised an exception",
                extra={"symbol": clean_sym, "error": str(exc)},
            )
        logger.warning("yfinance returned no data — will use fallback", extra={"symbol": clean_sym})
        return None

    @classmethod
    async def fetch_current_prices(cls, symbols: list[str]) -> dict[str, Decimal]:
        """
        Fetches current market prices using yfinance with a 1-hour TTL cache.
        Tries Redis first, then falls back to local memory TTLCache, then fetches from yfinance.
        """
        prices: dict[str, Decimal] = {}
        symbols_to_fetch: list[str] = []

        # Determine unique cleaned symbols
        cleaned_map = {}
        for sym in symbols:
            clean_sym = sym.upper().strip().split(".")[0]
            cleaned_map[sym.upper().strip()] = clean_sym

        unique_cleaned = list(set(cleaned_map.values()))

        # 1. Try Redis cache first
        redis = await cls._get_redis_client()
        redis_failed = False
        redis_cached: dict[str, Decimal] = {}

        if redis:
            try:
                keys = [f"tradesense:price:{sym}" for sym in unique_cleaned]
                cached_values = await redis.mget(keys)
                for sym, val in zip(unique_cleaned, cached_values):
                    if val is not None:
                        redis_cached[sym] = Decimal(str(val))
                        logger.debug("Redis cache hit", extra={"symbol": sym, "price": val})
            except Exception as e:
                logger.warning("Error reading from Redis cache, falling back to local cache", extra={"error": str(e)})
                redis_failed = True

        # 2. Check local TTLCache if Redis missed or failed
        for sym in unique_cleaned:
            if sym in redis_cached:
                prices[sym] = redis_cached[sym]
                continue

            local_cached = cls._price_cache.get(sym)
            if local_cached is not None:
                logger.debug("Local cache hit", extra={"symbol": sym})
                prices[sym] = local_cached
            else:
                symbols_to_fetch.append(sym)

        # 3. Fetch missing symbols from yfinance
        if symbols_to_fetch:
            logger.info("Fetching live prices", extra={"symbols": symbols_to_fetch, "count": len(symbols_to_fetch)})
            tasks = [
                asyncio.to_thread(cls._fetch_from_yfinance_sync, sym)
                for sym in symbols_to_fetch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            redis_updates = {}
            for clean_sym, res in zip(symbols_to_fetch, results):
                if isinstance(res, Exception) or res is None:
                    # Use mock as fallback (stale cache already evicted by TTLCache)
                    fallback = cls._MOCK_PRICES.get(clean_sym, Decimal("500.00"))
                    logger.warning(
                        "Using mock/fallback price",
                        extra={"symbol": clean_sym, "fallback_price": float(fallback)},
                    )
                    prices[clean_sym] = fallback
                else:
                    prices[clean_sym] = res
                    cls._price_cache[clean_sym] = res
                    redis_updates[f"tradesense:price:{clean_sym}"] = str(res)

            # 4. Write back to Redis cache
            if redis and redis_updates and not redis_failed:
                try:
                    async with redis.pipeline(transaction=False) as pipe:
                        for k, v in redis_updates.items():
                            pipe.set(k, v, ex=settings.market_data_cache_ttl_seconds)
                        await pipe.execute()
                    logger.debug("Redis cache updated in batch", extra={"keys": list(redis_updates.keys())})
                except Exception as e:
                    logger.warning("Failed to write to Redis cache", extra={"error": str(e)})

        # Map back to the original symbol format requested by the caller
        return {
            sym.upper().strip(): prices.get(
                cleaned_map[sym.upper().strip()],
                cls._MOCK_PRICES.get(cleaned_map[sym.upper().strip()], Decimal("500.00"))
            )
            for sym in symbols
        }

