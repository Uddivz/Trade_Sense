import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.market_data_service import MarketDataService

@pytest.fixture(autouse=True)
def reset_service_state():
    """Reset MarketDataService class variables between tests."""
    MarketDataService._redis_client = None
    MarketDataService._redis_available = True
    MarketDataService._last_redis_check = 0.0
    MarketDataService._price_cache.clear()
    yield
    # Teardown to prevent test pollution
    MarketDataService._price_cache.clear()
    MarketDataService._redis_client = None
    MarketDataService._redis_available = True

@pytest.mark.asyncio
async def test_redis_cache_hit():
    """Test that a price in the Redis cache is returned directly without querying yfinance."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    # Return "2500.00" for RELIANCE
    mock_redis.mget = AsyncMock(return_value=["2500.00"])
    mock_redis.pipeline = MagicMock() # Will not be called for hits

    with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
        # We query for RELIANCE
        prices = await MarketDataService.fetch_current_prices(["RELIANCE"])
        
        # Verify result
        assert prices["RELIANCE"] == Decimal("2500.00")
        # Verify Redis mget was called with correct namespace key
        mock_redis.mget.assert_called_once_with(["tradesense:price:RELIANCE"])

@pytest.mark.asyncio
async def test_redis_cache_miss_local_cache_hit():
    """Test that a Redis miss falls back to the local memory TTLCache."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.mget = AsyncMock(return_value=[None]) # Miss

    # Seed the local cache
    MarketDataService._price_cache["TCS"] = Decimal("3900.00")

    with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
        prices = await MarketDataService.fetch_current_prices(["TCS"])
        
        assert prices["TCS"] == Decimal("3900.00")
        mock_redis.mget.assert_called_once_with(["tradesense:price:TCS"])

@pytest.mark.asyncio
async def test_redis_connection_failure_fallback():
    """Test that Redis connection failures fall back to local caching/mocks gracefully."""
    # Force _fetch_from_yfinance_sync to return a known mock value or mock it directly
    with patch("redis.asyncio.Redis.from_url", side_effect=Exception("Connection refused")):
        # Query a symbol that is not cached anywhere. It should use mock fallback (ITC = 440)
        prices = await MarketDataService.fetch_current_prices(["ITC"])
        
        assert prices["ITC"] == Decimal("440.00")
        # Verify that _redis_available has been set to False due to error
        assert MarketDataService._redis_available is False
        assert MarketDataService._redis_client is None

@pytest.mark.asyncio
async def test_redis_write_back_on_miss():
    """Test that successful fetches update both local cache and Redis."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.mget = AsyncMock(return_value=[None]) # Miss
    
    # Mock pipeline for batch writing (pipeline is a synchronous call returning an async context manager)
    mock_pipeline = MagicMock()
    mock_pipeline.set = MagicMock()
    mock_pipeline.execute = AsyncMock()
    mock_redis.pipeline = MagicMock()
    mock_redis.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_pipeline)
    mock_redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock yfinance call to avoid external dependency
    with patch("redis.asyncio.Redis.from_url", return_value=mock_redis), \
         patch.object(MarketDataService, "_fetch_from_yfinance_sync", return_value=Decimal("1500.00")) as mock_fetch:
        
        prices = await MarketDataService.fetch_current_prices(["INFY"])
        
        assert prices["INFY"] == Decimal("1500.00")
        mock_fetch.assert_called_once_with("INFY")
        
        # Verify local cache update
        assert MarketDataService._price_cache["INFY"] == Decimal("1500.00")
        
        # Verify Redis pipeline set was called with TTL
        mock_pipeline.set.assert_called_once_with(
            "tradesense:price:INFY", 
            "1500.00", 
            ex=MarketDataService.CACHE_TTL_SECONDS
        )
        mock_pipeline.execute.assert_called_once()
