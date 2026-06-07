"""
TradeSense — Test: Health Endpoint
Smoke test verifying the FastAPI app initialises and the /health route responds.
Note: In CI this uses a test database. In local dev, ensure Docker is running.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_root_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "TradeSense" in data["message"]


@pytest.mark.asyncio
async def test_health_returns_service_name():
    """
    Health endpoint must return service name and version.
    DB connectivity status is allowed to be 'unreachable' in unit test context.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["service"] == "TradeSense API"
    assert "database" in data
    assert "version" in data
