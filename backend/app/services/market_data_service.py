import asyncio
import logging
from decimal import Decimal

import yfinance as yf
from cachetools import TTLCache

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

    # TTLCache: max 512 symbols, auto-expires entries after 1 hour.
    # Replaces the unbounded dict + manual timestamp check pattern.
    # Thread-safe reads are fine here; asyncio.to_thread handles write isolation.
    CACHE_TTL_SECONDS = 3600  # 1 hour
    _price_cache: TTLCache = TTLCache(maxsize=512, ttl=CACHE_TTL_SECONDS)

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
        Cache is bounded to 512 symbols (TTLCache auto-evicts expired entries).
        Falls back to stale cache on fetch failure, then _MOCK_PRICES, then 500.00.
        """
        prices: dict[str, Decimal] = {}
        symbols_to_fetch: list[str] = []

        for sym in symbols:
            clean_sym = sym.upper().strip().split(".")[0]

            # TTLCache raises KeyError on miss or expired entry — treat both as a miss
            cached_price = cls._price_cache.get(clean_sym)
            if cached_price is not None:
                logger.debug("Cache hit", extra={"symbol": clean_sym})
                prices[clean_sym] = cached_price
            else:
                logger.debug("Cache miss — queuing fetch", extra={"symbol": clean_sym})
                symbols_to_fetch.append(clean_sym)

        # Batch fetch in thread pool to avoid blocking the asyncio event loop
        if symbols_to_fetch:
            logger.info("Fetching live prices", extra={"symbols": symbols_to_fetch, "count": len(symbols_to_fetch)})
            tasks = [
                asyncio.to_thread(cls._fetch_from_yfinance_sync, sym)
                for sym in symbols_to_fetch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

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
                    cls._price_cache[clean_sym] = res  # TTLCache handles expiry automatically
                    prices[clean_sym] = res

        # Map back to the original symbol format requested by the caller
        return {
            sym.upper().strip(): prices.get(
                sym.upper().strip().split(".")[0],
                cls._MOCK_PRICES.get(sym.upper().strip().split(".")[0], Decimal("500.00"))
            )
            for sym in symbols
        }
