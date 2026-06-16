"""
TradeSense — Tests: Auth & Portfolio CRUD
Verifies registration, password strength, login, get_current_user dependency,
and portfolio creation/retrieval.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.database import AsyncSessionLocal, engine
from app.models.user import User
from app.models.portfolio import Portfolio


@pytest.fixture(autouse=True)
async def cleanup_db():
    """
    Cleans up all test users (and cascading portfolios) created during tests.
    """
    yield
    async with AsyncSessionLocal() as session:
        # Retrieve all users created with 'test_' prefix in email
        result = await session.execute(
            select(User).where(User.email.like("test_%"))
        )
        test_users = result.scalars().all()
        for user in test_users:
            await session.delete(user)
        await session.commit()
    # Dispose the engine to cleanly close any pooled connections before loop exit
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_registration_and_login():
    """
    Test user registration, login, and access token retrieval.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Register a new user
        reg_payload = {
            "email": "test_user_auth@example.com",
            "password": "SecurePassword123",
            "full_name": "Test User",
        }
        reg_response = await client.post("/v1/auth/register", json=reg_payload)
        assert reg_response.status_code == 201
        user_data = reg_response.json()
        assert user_data["email"] == "test_user_auth@example.com"
        assert "id" in user_data
        assert user_data["is_active"] is True

        # Try registering the same user again (should fail)
        dup_response = await client.post("/v1/auth/register", json=reg_payload)
        assert dup_response.status_code == 400
        assert dup_response.json()["detail"] == "Email already registered"

        # Try registering with weak password (should fail)
        weak_payload = {
            "email": "test_weak@example.com",
            "password": "weak",
            "full_name": "Weak User",
        }
        weak_response = await client.post("/v1/auth/register", json=weak_payload)
        assert weak_response.status_code == 422

        # 2. Login to get JWT token
        login_data = {
            "username": "test_user_auth@example.com",
            "password": "SecurePassword123",
        }
        login_response = await client.post("/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_secured_portfolio_crud():
    """
    Test that portfolio creation and retrieval endpoints require authentication,
    and work correctly for authenticated users.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Try to create portfolio without authentication (should fail)
        port_payload = {
            "name": "My Test Portfolio",
            "broker_name": "Zerodha",
            "currency": "INR",
            "cost_basis_method": "FIFO",
        }
        fail_create = await client.post("/v1/portfolios/", json=port_payload)
        assert fail_create.status_code == 401

        # Try to list portfolios without authentication (should fail)
        fail_list = await client.get("/v1/portfolios/")
        assert fail_list.status_code == 401

        # 2. Register and login to get authorization headers
        reg_payload = {
            "email": "test_portfolio_owner@example.com",
            "password": "SecurePassword123",
            "full_name": "Portfolio Owner",
        }
        await client.post("/v1/auth/register", json=reg_payload)

        login_data = {
            "username": "test_portfolio_owner@example.com",
            "password": "SecurePassword123",
        }
        login_res = await client.post("/v1/auth/login", data=login_data)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create a portfolio (should succeed and be default)
        create_res = await client.post(
            "/v1/portfolios/", json=port_payload, headers=headers
        )
        assert create_res.status_code == 201
        port_data = create_res.json()
        assert port_data["name"] == "My Test Portfolio"
        assert port_data["is_default"] is True
        assert port_data["broker_name"] == "Zerodha"

        # Create a second portfolio (should succeed and NOT be default)
        port_payload_2 = {
            "name": "My Second Portfolio",
            "broker_name": "Groww",
            "currency": "INR",
            "cost_basis_method": "FIFO",
        }
        create_res_2 = await client.post(
            "/v1/portfolios/", json=port_payload_2, headers=headers
        )
        assert create_res_2.status_code == 201
        port_data_2 = create_res_2.json()
        assert port_data_2["name"] == "My Second Portfolio"
        assert port_data_2["is_default"] is False

        # 4. List portfolios (should return both portfolios in order of creation)
        list_res = await client.get("/v1/portfolios/", headers=headers)
        assert list_res.status_code == 200
        portfolios = list_res.json()
        assert len(portfolios) == 2
        # Order should be desc created_at (second created should be first in list)
        assert portfolios[0]["name"] == "My Second Portfolio"
        assert portfolios[1]["name"] == "My Test Portfolio"
