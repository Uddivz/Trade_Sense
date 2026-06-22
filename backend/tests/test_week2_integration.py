import pytest
import io
from decimal import Decimal
from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.models.user import User
from app.models.portfolio import Portfolio

# ---------------------------------------------------------------------------
# Sample Zerodha CSV — matches the active ZerodhaParser column expectations
# ---------------------------------------------------------------------------
SAMPLE_CSV = """Symbol,ISIN,Trade Date,Type,Quantity,Price,Brokerage,STT,Other charges,Trade ID
TCS,INE467B01029,2023-10-01,BUY,10,3500.00,20.00,35.00,10.00,TRD-W2-001
TCS,INE467B01029,2023-10-02,SELL,5,3600.00,10.00,18.00,5.00,TRD-W2-002
INFY,INE009A01021,2023-10-01,BUY,20,1500.00,20.00,30.00,5.00,TRD-W2-003
"""


@pytest.mark.asyncio
@patch("app.services.market_data_service.MarketDataService.fetch_current_prices")
async def test_week2_integration_upload_and_holdings(mock_fetch_prices):
    """
    Full week-2 integration test: Register → Login → Create Portfolio →
    Upload CSV → Verify Transactions (paginated) → Verify Holdings.
    Uses the same real-HTTP approach as test_csv_upload_pipeline.
    """
    mock_fetch_prices.return_value = {
        "TCS": Decimal("3700.00"),
        "INFY": Decimal("1600.00"),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Register --------------------------------------------------------
        await ac.post(
            "/v1/auth/register",
            json={
                "email": "test_w2_integration@example.com",
                "password": "TestPassword1",
                "full_name": "Week2 Integration",
            },
        )

        # 2. Login -----------------------------------------------------------
        login_res = await ac.post(
            "/v1/auth/login",
            data={
                "username": "test_w2_integration@example.com",
                "password": "TestPassword1",
            },
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create portfolio ------------------------------------------------
        port_res = await ac.post(
            "/v1/portfolios/",
            json={"name": "Week2 Integration Portfolio"},
            headers=headers,
        )
        assert port_res.status_code == 201
        portfolio_id = port_res.json()["id"]

        # 4. Upload CSV ------------------------------------------------------
        files = {
            "file": ("zerodha_trades.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")
        }
        upload_res = await ac.post(
            f"/v1/uploads/csv?portfolio_id={portfolio_id}",
            files=files,
            headers=headers,
        )
        assert upload_res.status_code == 201
        data = upload_res.json()
        assert data["records_parsed"] == 3
        assert data["records_inserted"] == 3

        # 5. Re-upload — deduplication check ---------------------------------
        files = {
            "file": ("zerodha_trades.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")
        }
        re_upload_res = await ac.post(
            f"/v1/uploads/csv?portfolio_id={portfolio_id}",
            files=files,
            headers=headers,
        )
        assert re_upload_res.status_code == 201
        assert re_upload_res.json()["records_inserted"] == 0

        # 6. Verify transactions (paginated envelope) -------------------------
        tx_res = await ac.get(
            f"/v1/portfolios/{portfolio_id}/transactions",
            headers=headers,
        )
        assert tx_res.status_code == 200
        envelope = tx_res.json()
        assert envelope["total"] == 3
        assert envelope["page"] == 1
        assert len(envelope["items"]) == 3

        # 7. Verify holdings -------------------------------------------------
        holdings_res = await ac.get(
            f"/v1/portfolios/{portfolio_id}/holdings",
            headers=headers,
        )
        assert holdings_res.status_code == 200
        holdings = holdings_res.json()

        # TCS: 10 @ 3500 bought, 5 @ 3600 sold → 5 remaining @ avg 3500
        # INFY: 20 @ 1500 bought → 20 remaining
        assert len(holdings) == 2

        tcs = next(h for h in holdings if h["symbol"] == "TCS")
        # FIFO cost-basis includes charges: net_value=35065, qty=10 → avg=3506.5
        assert Decimal(tcs["quantity"]) == Decimal("5")
        assert Decimal(tcs["average_cost"]) == Decimal("3506.5")
        # sell net_value = 18000-10-18-5 = 17967 → sell_ppu = 3593.4
        # realized_pnl = (3593.4 - 3506.5) × 5 = 434.5
        assert Decimal(tcs["realized_pnl"]) == Decimal("434.5")
        # unrealized_pnl = 5 × (3700 - 3506.5) = 967.5
        assert Decimal(tcs["unrealized_pnl"]) == Decimal("967.5")

        infy = next(h for h in holdings if h["symbol"] == "INFY")
        # INFY BUY net_value = 30000+20+30+5 = 30055 → avg=1502.75
        assert Decimal(infy["quantity"]) == Decimal("20")
        assert Decimal(infy["realized_pnl"]) == Decimal("0")
