import pytest
from decimal import Decimal
from datetime import date
from app.services.portfolio_tracker import FIFOPortfolioTracker

class MockTransaction:
    def __init__(self, symbol, transaction_type, quantity, net_value, trade_date):
        self.symbol = symbol
        self.transaction_type = transaction_type
        self.quantity = quantity
        self.net_value = net_value
        self.trade_date = trade_date

def test_fifo_tracker_simple_buy():
    tracker = FIFOPortfolioTracker()
    transactions = [
        MockTransaction("AAPL", "BUY", 10, 1500.0, date(2023, 1, 1))
    ]
    summary = tracker.process_transactions(transactions)
    
    assert "AAPL" in summary
    assert summary["AAPL"]["quantity"] == Decimal("10")
    assert summary["AAPL"]["avg_cost_basis"] == Decimal("150.0")
    assert summary["AAPL"]["realized_pnl"] == Decimal("0")

def test_fifo_tracker_buy_and_partial_sell():
    tracker = FIFOPortfolioTracker()
    transactions = [
        MockTransaction("AAPL", "BUY", 10, 1500.0, date(2023, 1, 1)),
        MockTransaction("AAPL", "SELL", 5, 800.0, date(2023, 1, 2))
    ]
    summary = tracker.process_transactions(transactions)
    
    assert summary["AAPL"]["quantity"] == Decimal("5")
    assert summary["AAPL"]["avg_cost_basis"] == Decimal("150.0")
    # PnL for 5 shares: 5 * (160 - 150) = 50.0
    assert summary["AAPL"]["realized_pnl"] == Decimal("50.0")

def test_fifo_tracker_multiple_lots():
    tracker = FIFOPortfolioTracker()
    transactions = [
        MockTransaction("MSFT", "BUY", 10, 1000.0, date(2023, 1, 1)), # 100 per share
        MockTransaction("MSFT", "BUY", 10, 1200.0, date(2023, 1, 2)), # 120 per share
        MockTransaction("MSFT", "SELL", 15, 2100.0, date(2023, 1, 3)) # 140 per share
    ]
    summary = tracker.process_transactions(transactions)
    
    # Sell 15: 10 from lot 1 (cost 100), 5 from lot 2 (cost 120)
    # Remaining: 5 from lot 2 (cost 120)
    assert summary["MSFT"]["quantity"] == Decimal("5")
    assert summary["MSFT"]["avg_cost_basis"] == Decimal("120.0")
    
    # Realized PnL:
    # Lot 1: 10 * (140 - 100) = 400
    # Lot 2: 5 * (140 - 120) = 100
    # Total = 500
    assert summary["MSFT"]["realized_pnl"] == Decimal("500.0")

def test_fifo_tracker_full_liquidation():
    tracker = FIFOPortfolioTracker()
    transactions = [
        MockTransaction("GOOG", "BUY", 5, 500.0, date(2023, 1, 1)), # 100 per share
        MockTransaction("GOOG", "SELL", 5, 600.0, date(2023, 1, 2)) # 120 per share
    ]
    summary = tracker.process_transactions(transactions)
    
    assert summary["GOOG"]["quantity"] == Decimal("0")
    assert summary["GOOG"]["avg_cost_basis"] == Decimal("0")
    assert summary["GOOG"]["realized_pnl"] == Decimal("100.0")

def test_fifo_tracker_selling_more_than_owned_raises_error():
    tracker = FIFOPortfolioTracker()
    transactions = [
        MockTransaction("TSLA", "BUY", 5, 500.0, date(2023, 1, 1)),
        MockTransaction("TSLA", "SELL", 10, 1000.0, date(2023, 1, 2))
    ]
    
    with pytest.raises(ValueError, match="Invalid sell: Selling more than owned for TSLA"):
        tracker.process_transactions(transactions)

def test_fifo_tracker_fractional_shares():
    tracker = FIFOPortfolioTracker()
    transactions = [
        MockTransaction("BTC", "BUY", 0.5, 10000.0, date(2023, 1, 1)), # 20000 per unit
        MockTransaction("BTC", "SELL", 0.1, 2500.0, date(2023, 1, 2)) # 25000 per unit
    ]
    summary = tracker.process_transactions(transactions)
    
    assert summary["BTC"]["quantity"] == Decimal("0.4")
    assert summary["BTC"]["avg_cost_basis"] == Decimal("20000.0")
    assert summary["BTC"]["realized_pnl"] == Decimal("500.0")

def test_fifo_tracker_same_day_buy_and_sell():
    tracker = FIFOPortfolioTracker()
    transactions = [
        MockTransaction("AMZN", "SELL", 5, 600.0, date(2023, 1, 1)), # SELL should be processed after BUY
        MockTransaction("AMZN", "BUY", 10, 1000.0, date(2023, 1, 1)),
    ]
    summary = tracker.process_transactions(transactions)
    
    assert summary["AMZN"]["quantity"] == Decimal("5")
    assert summary["AMZN"]["avg_cost_basis"] == Decimal("100.0")
    # PnL: 5 * (120 - 100) = 100
    assert summary["AMZN"]["realized_pnl"] == Decimal("100.0")
