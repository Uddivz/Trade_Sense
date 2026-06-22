import pytest
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from app.services.analytics.engine import AnalyticsEngine
from app.models.holding import Holding
from app.models.transaction import Transaction

# Mock test for the engine logic directly bypassing the HTTP layer.
# Assumes SQLite async testing session from conftest.py

@pytest.mark.asyncio
async def test_analytics_engine_empty_portfolio(db_session):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    engine = AnalyticsEngine(db_session)
    metric = await engine.compute_metrics(user_id=user_id, portfolio_id=portfolio_id)
    
    assert metric is None


@pytest.mark.asyncio
async def test_analytics_engine_computes_correctly(db_session):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Insert mock transactions
    tx1 = Transaction(
        portfolio_id=portfolio_id, symbol="TCS", transaction_type="BUY",
        quantity=Decimal("10"), price=Decimal("100"), total_value=Decimal("1000"), net_value=Decimal("1000"),
        trade_date=date(2023, 1, 1)
    )
    tx2 = Transaction(
        portfolio_id=portfolio_id, symbol="TCS", transaction_type="SELL",
        quantity=Decimal("10"), price=Decimal("150"), total_value=Decimal("1500"), net_value=Decimal("1500"),
        trade_date=date(2023, 1, 2)
    )
    db_session.add_all([tx1, tx2])
    
    # Insert mock holdings
    h1 = Holding(
        portfolio_id=portfolio_id, symbol="INFY", quantity=Decimal("10"),
        average_cost=Decimal("100"), market_price=Decimal("110"),
        market_value=Decimal("1100"), unrealized_pnl=Decimal("100"), realized_pnl=Decimal("500")
    )
    db_session.add(h1)
    await db_session.commit()
    
    engine = AnalyticsEngine(db_session)
    metric = await engine.compute_metrics(user_id=user_id, portfolio_id=portfolio_id)
    
    assert metric is not None
    assert metric.user_id == user_id
    assert metric.portfolio_id == portfolio_id
    
    # Realized gains = 500. Unrealized = 100.
    # PGR = 500 / 600 = 0.83333
    assert float(metric.pgr) == pytest.approx(0.83333, rel=1e-3)
    
    # Realized/Unrealized losses = 0
    assert float(metric.plr) == 0.0
    
    # DE = 0.8333 - 0 = 0.8333
    assert float(metric.disposition_effect_score) == pytest.approx(0.83333, rel=1e-3)
    
    # HHI (1 position = 100%)
    assert float(metric.hhi) == 10000.0
