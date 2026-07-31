import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
import uuid

from app.main import app
from app.database import AsyncSessionLocal, engine
from app.models.user import User

# Sample CSV contents for tests
ZERODHA_CSV = """Symbol,ISIN,Trade Date,Type,Quantity,Price,Brokerage,STT,Other charges,Trade ID
TCS,INE467B01029,2026-06-15,BUY,10,3800.00,20.00,38.00,10.00,TRD-Z-101
INFY,INE009A01021,2026-06-16,BUY,5,1500.00,10.00,15.00,5.00,TRD-Z-102
TCS,INE467B01029,2026-06-17,SELL,5,3900.00,20.00,39.00,10.00,TRD-Z-103
"""

@pytest.fixture(autouse=True)
async def cleanup_db():
    yield
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email.like("test_ml_%"))
        )
        test_users = result.scalars().all()
        for user in test_users:
            await session.delete(user)
        await session.commit()
    await engine.dispose()

@pytest.mark.asyncio
async def test_ml_risk_score_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Register and login
        reg_payload = {
            "email": "test_ml_user@example.com",
            "password": "SecurePassword123",
            "full_name": "ML Tester",
        }
        await client.post("/v1/auth/register", json=reg_payload)

        login_data = {
            "username": "test_ml_user@example.com",
            "password": "SecurePassword123",
        }
        login_res = await client.post("/v1/auth/login", data=login_data)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a portfolio
        port_payload = {"name": "ML Test Portfolio", "broker_name": "Zerodha"}
        create_res = await client.post("/v1/portfolios/", json=port_payload, headers=headers)
        assert create_res.status_code == 201
        portfolio_id = create_res.json()["id"]

        # 3. Request ML risk score before uploading a CSV (should fail with 404 because no metrics computed yet)
        fail_res = await client.get(
            f"/v1/analytics/ml-risk-score?portfolio_id={portfolio_id}",
            headers=headers
        )
        assert fail_res.status_code == 404
        assert "No behavioral metrics found" in fail_res.json()["detail"]

        # 4. Upload Zerodha CSV to trigger metric computation
        files = {"file": ("zerodha_trades.csv", ZERODHA_CSV, "text/csv")}
        upload_res = await client.post(
            f"/v1/uploads/csv?portfolio_id={portfolio_id}",
            files=files,
            headers=headers
        )
        assert upload_res.status_code == 201

        # 5. Retrieve the ML risk score and explanation report
        risk_res = await client.get(
            f"/v1/analytics/ml-risk-score?portfolio_id={portfolio_id}",
            headers=headers
        )
        assert risk_res.status_code == 200
        risk_data = risk_res.json()
        
        # Verify MLRiskScoreResponse fields
        assert risk_data["portfolio_id"] == portfolio_id
        assert risk_data["risk_label"] in ["LOW", "MEDIUM", "HIGH"]
        assert 0.0 <= risk_data["confidence"] <= 1.0
        assert "model_version" in risk_data
        assert "computed_at" in risk_data
        
        # Verify SHAP / feature importance explanations
        shap_explanation = risk_data["shap_explanation"]
        assert len(shap_explanation) > 0
        for contribution in shap_explanation:
            assert "feature" in contribution
            assert "value" in contribution
            assert "shap_value" in contribution
            assert "direction" in contribution
            assert contribution["direction"] in ["increases_risk", "reduces_risk"]

        # Check security: accessing from unauthorized user should return 404/401
        # Create second user
        reg_payload2 = {
            "email": "test_ml_user2@example.com",
            "password": "SecurePassword123",
            "full_name": "ML Tester 2",
        }
        await client.post("/v1/auth/register", json=reg_payload2)
        login_res2 = await client.post("/v1/auth/login", data={"username": "test_ml_user2@example.com", "password": "SecurePassword123"})
        token2 = login_res2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        unauth_res = await client.get(
            f"/v1/analytics/ml-risk-score?portfolio_id={portfolio_id}",
            headers=headers2
        )
        assert unauth_res.status_code == 404

@pytest.mark.asyncio
async def test_anomalies_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Register and login
        reg_payload = {
            "email": "test_anom_user@example.com",
            "password": "SecurePassword123",
            "full_name": "Anomaly Tester",
        }
        await client.post("/v1/auth/register", json=reg_payload)

        login_res = await client.post("/v1/auth/login", data={"username": "test_anom_user@example.com", "password": "SecurePassword123"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a portfolio
        port_payload = {"name": "Anom Test Portfolio", "broker_name": "Zerodha"}
        create_res = await client.post("/v1/portfolios/", json=port_payload, headers=headers)
        portfolio_id = create_res.json()["id"]

        # 3. Upload CSV
        files = {"file": ("zerodha_trades.csv", ZERODHA_CSV, "text/csv")}
        await client.post(f"/v1/uploads/csv?portfolio_id={portfolio_id}", files=files, headers=headers)

        # 4. Get anomalies
        res = await client.get(f"/v1/analytics/{portfolio_id}/anomalies", headers=headers)
        assert res.status_code == 200
        
        data = res.json()
        assert data["portfolio_id"] == portfolio_id
        assert "anomalies" in data
        assert isinstance(data["anomalies"], list)
        
        # Test auth
        login_res2 = await client.post("/v1/auth/login", data={"username": "test_ml_user2@example.com", "password": "SecurePassword123"})
        if login_res2.status_code == 200:
            headers2 = {"Authorization": f"Bearer {login_res2.json()['access_token']}"}
            unauth_res = await client.get(f"/v1/analytics/{portfolio_id}/anomalies", headers=headers2)
            assert unauth_res.status_code == 404
