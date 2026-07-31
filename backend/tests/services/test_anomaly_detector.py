import pytest
import uuid
from datetime import datetime, timedelta, timezone
from app.services.ml.anomaly_detector import AnomalyDetectorService, anomaly_detector
from unittest.mock import MagicMock

class MockTransaction:
    def __init__(self, id, symbol, type, total_value, trade_date):
        self.id = id
        self.symbol = symbol
        self.transaction_type = type
        self.total_value = total_value
        self.trade_date = trade_date

def test_anomaly_detector_loads():
    # It should either load the model or fallback without crashing
    svc = AnomalyDetectorService()
    assert hasattr(svc, 'is_loaded')

def test_detect_anomalies_empty():
    svc = AnomalyDetectorService()
    res = svc.detect_anomalies([], 10000)
    assert res == []

def test_detect_anomalies_fallback():
    # Force fallback
    svc = AnomalyDetectorService()
    svc.is_loaded = False
    
    base_date = datetime(2023, 1, 1).date()
    
    # 5 trades on the same day -> triggers "High Frequency Trading (Overtrading)"
    txs = [
        MockTransaction(uuid.uuid4(), "AAPL", "BUY", 1000, base_date),
        MockTransaction(uuid.uuid4(), "TSLA", "BUY", 1000, base_date),
        MockTransaction(uuid.uuid4(), "MSFT", "BUY", 1000, base_date),
        MockTransaction(uuid.uuid4(), "AMZN", "BUY", 1000, base_date),
        MockTransaction(uuid.uuid4(), "GOOG", "BUY", 1000, base_date),
        MockTransaction(uuid.uuid4(), "NFLX", "SELL", 3000, base_date), # Huge dump, > 20% of 10000
    ]
    
    anomalies = svc.detect_anomalies(txs, 10000)
    
    # Expect at least one anomaly due to high frequency and large dump
    assert len(anomalies) > 0
    assert any("High Frequency Trading (Overtrading)" in a["flags"] for a in anomalies)
