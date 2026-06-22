import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from decimal import Decimal
from datetime import date
import uuid

from app.main import app
from app.database import AsyncSessionLocal, engine
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.holding import Holding

from app.services.parser.detector import detect_broker, BrokerEnum
from app.services.parser.zerodha import ZerodhaParser
from app.services.parser.groww import GrowwParser
# BUG-04 FIX: FIFOCostBasisEngine does not exist. The real class is FIFOPortfolioTracker
# in portfolio_tracker.py with a process_transactions() instance method.
from app.services.portfolio_tracker import FIFOPortfolioTracker


# Sample CSV contents for tests
ZERODHA_VALID_CSV = """Symbol,ISIN,Trade Date,Type,Quantity,Price,Brokerage,STT,Other charges,Trade ID
TCS,INE467B01029,2026-06-15,BUY,10,3800.00,20.00,38.00,10.00,TRD-Z-001
INFY,INE009A01021,2026-06-16,BUY,5,1500.00,10.00,15.00,5.00,TRD-Z-002
TCS,INE467B01029,2026-06-17,SELL,5,3900.00,20.00,39.00,10.00,TRD-Z-003
"""

GROWW_VALID_CSV = """Groww Transaction ID,Date,Activity,Symbol,Quantity,Price,Amount
TRD-G-001,2026-06-15,BUY,TCS,10,3800.00,38000.00
TRD-G-002,2026-06-16,BUY,INFY,5,1500.00,7500.00
TRD-G-003,2026-06-17,SELL,TCS,5,3900.00,19500.00
"""

INVALID_CSV = """Some,Random,Headers,That,Are,Not,Supported
1,2,3,4,5,6,7
"""


@pytest.fixture(autouse=True)
async def cleanup_db():
    """
    Cleans up all test users (and cascading portfolios/transactions/holdings) created during tests.
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
    await engine.dispose()


# ── Unit Tests ──────────────────────────────────────────────────────────────────

def test_broker_detection():
    assert detect_broker(ZERODHA_VALID_CSV) == BrokerEnum.ZERODHA
    assert detect_broker(GROWW_VALID_CSV) == BrokerEnum.GROWW
    with pytest.raises(ValueError):
        detect_broker(INVALID_CSV)


def test_zerodha_parser():
    parser = ZerodhaParser()
    records = parser.parse(ZERODHA_VALID_CSV)
    assert len(records) == 3
    
    # Assert Buy TCS
    assert records[0]["symbol"] == "TCS"
    assert records[0]["transaction_type"] == "BUY"
    assert records[0]["quantity"] == Decimal("10")
    assert records[0]["price"] == Decimal("3800.00")
    assert records[0]["broker_trade_id"] == "TRD-Z-001"
    assert records[0]["net_value"] == Decimal("38068.00") # 38000 + 20 + 38 + 10


def test_groww_parser():
    parser = GrowwParser()
    records = parser.parse(GROWW_VALID_CSV)
    assert len(records) == 3
    
    # Assert Sell TCS
    assert records[2]["symbol"] == "TCS"
    assert records[2]["transaction_type"] == "SELL"
    assert records[2]["quantity"] == Decimal("5")
    assert records[2]["price"] == Decimal("3900.00")
    assert records[2]["broker_trade_id"] == "TRD-G-003"
    assert records[2]["net_value"] == Decimal("19500.00")


def test_fifo_portfolio_tracker():
    # BUG-04 FIX: Rewrote using the real FIFOPortfolioTracker API.
    # - Class is instantiated (not a static class method)
    # - Method is process_transactions(), not calculate_holdings()
    # - dict key is "avg_cost_basis" (from portfolio_tracker.py)
    # - ValueError message matches the actual raise in portfolio_tracker.py
    portfolio_id = uuid.uuid4()
    tx1 = Transaction(
        portfolio_id=portfolio_id,
        symbol="TCS",
        transaction_type="BUY",
        quantity=Decimal("10"),
        price=Decimal("3800.00"),
        net_value=Decimal("38068.00"),  # cost basis per unit = 3806.8
        trade_date=date(2026, 6, 15),
        total_value=Decimal("38000.00"),
    )
    tx2 = Transaction(
        portfolio_id=portfolio_id,
        symbol="TCS",
        transaction_type="SELL",
        quantity=Decimal("5"),
        price=Decimal("3900.00"),
        net_value=Decimal("38931.00"),
        trade_date=date(2026, 6, 17),
        total_value=Decimal("19500.00"),
    )

    # 1. Successful FIFO calculation
    tracker = FIFOPortfolioTracker()
    summary = tracker.process_transactions([tx1, tx2])
    assert "TCS" in summary
    assert summary["TCS"]["quantity"] == Decimal("5")
    assert summary["TCS"]["avg_cost_basis"] == Decimal("3806.8")

    # 2. Overselling check — actual error message from portfolio_tracker.py line 51
    tx3 = Transaction(
        portfolio_id=portfolio_id,
        symbol="TCS",
        transaction_type="SELL",
        quantity=Decimal("12"),
        price=Decimal("3900.00"),
        net_value=Decimal("46800.00"),
        trade_date=date(2026, 6, 17),
        total_value=Decimal("46800.00"),
    )
    with pytest.raises(ValueError, match="Invalid sell"):
        tracker2 = FIFOPortfolioTracker()
        tracker2.process_transactions([tx1, tx3])


# ── API Integration Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_csv_upload_pipeline():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Register and login
        reg_payload = {
            "email": "test_uploader@example.com",
            "password": "SecurePassword123",
            "full_name": "CSV Uploader",
        }
        await client.post("/v1/auth/register", json=reg_payload)

        login_data = {
            "username": "test_uploader@example.com",
            "password": "SecurePassword123",
        }
        login_res = await client.post("/v1/auth/login", data=login_data)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a portfolio
        port_payload = {"name": "Zerodha Ingestion Test", "broker_name": "Zerodha"}
        create_res = await client.post("/v1/portfolios/", json=port_payload, headers=headers)
        portfolio_id = create_res.json()["id"]

        # 3. Upload Zerodha CSV
        files = {
            "file": ("zerodha_trades.csv", ZERODHA_VALID_CSV, "text/csv")
        }
        upload_res = await client.post(
            f"/v1/uploads/csv?portfolio_id={portfolio_id}",
            files=files,
            headers=headers
        )
        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        assert upload_data["status"] == "success"
        assert upload_data["records_parsed"] == 3
        assert upload_data["records_inserted"] == 3
        assert upload_data["records_skipped"] == 0

        # 4. Check transactions retrieved from DB
        tx_res = await client.get(
            f"/v1/portfolios/{portfolio_id}/transactions",
            headers=headers
        )
        assert tx_res.status_code == 200
        txs = tx_res.json()
        # Paginated envelope: assert metadata
        assert txs["total"] == 3
        assert txs["page"] == 1
        assert txs["total_pages"] == 1
        items = txs["items"]
        assert len(items) == 3
        # Assert order: trade date DESC
        assert items[0]["symbol"] == "TCS"
        assert items[0]["transaction_type"] == "SELL"
        assert items[1]["symbol"] == "INFY"
        assert items[2]["symbol"] == "TCS"
        assert items[2]["transaction_type"] == "BUY"

        # 5. Check holdings database state
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Holding).where(Holding.portfolio_id == uuid.UUID(portfolio_id))
            )
            holdings = result.scalars().all()
            assert len(holdings) == 2
            
            holdings_map = {h.symbol: h for h in holdings}
            assert "TCS" in holdings_map
            assert Decimal(str(holdings_map["TCS"].quantity)) == Decimal("5")
            # BUG-04 FIX: Holding ORM model uses average_cost (renamed by Week-2 migration)
            assert Decimal(str(holdings_map["TCS"].average_cost)) == Decimal("3806.8000")
            # BUG-04 FIX: market_price, not current_price
            assert Decimal(str(holdings_map["TCS"].market_price)) == Decimal("3950.0000")
            assert Decimal(str(holdings_map["TCS"].unrealized_pnl)) == Decimal("716.0000")

            assert "INFY" in holdings_map
            assert Decimal(str(holdings_map["INFY"].quantity)) == Decimal("5")
            assert Decimal(str(holdings_map["INFY"].average_cost)) == Decimal("1506.0000")
            assert Decimal(str(holdings_map["INFY"].market_price)) == Decimal("1560.5000")
            assert Decimal(str(holdings_map["INFY"].unrealized_pnl)) == Decimal("272.5000")

        # 6. Test deduplication: Re-uploading the same file
        re_upload_res = await client.post(
            f"/v1/uploads/csv?portfolio_id={portfolio_id}",
            files=files,
            headers=headers
        )
        assert re_upload_res.status_code == 201
        re_upload_data = re_upload_res.json()
        assert re_upload_data["records_parsed"] == 3
        assert re_upload_data["records_inserted"] == 0
        assert re_upload_data["records_skipped"] == 3


@pytest.mark.asyncio
async def test_overselling_error_returns_400():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register and login
        reg_payload = {
            "email": "test_overseller@example.com",
            "password": "SecurePassword123",
            "full_name": "Overseller",
        }
        await client.post("/v1/auth/register", json=reg_payload)

        login_data = {
            "username": "test_overseller@example.com",
            "password": "SecurePassword123",
        }
        login_res = await client.post("/v1/auth/login", data=login_data)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create portfolio
        port_payload = {"name": "Overselling Test"}
        create_res = await client.post("/v1/portfolios/", json=port_payload, headers=headers)
        portfolio_id = create_res.json()["id"]

        # CSV with 10 BUY and 15 SELL of TCS
        oversell_csv = """Symbol,ISIN,Trade Date,Type,Quantity,Price,Brokerage,STT,Other charges,Trade ID
TCS,INE467B01029,2026-06-15,BUY,10,3800.00,0,0,0,TRD-Z-OVERS1
TCS,INE467B01029,2026-06-16,SELL,15,3900.00,0,0,0,TRD-Z-OVERS2
"""
        files = {"file": ("oversell_trades.csv", oversell_csv, "text/csv")}
        res = await client.post(
            f"/v1/uploads/csv?portfolio_id={portfolio_id}",
            files=files,
            headers=headers
        )
        assert res.status_code == 400
        # BUG-04 FIX: Match the actual ValueError message from portfolio_tracker.py
        assert "Invalid sell" in res.json()["detail"]
