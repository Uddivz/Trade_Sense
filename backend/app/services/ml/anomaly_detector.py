"""
TradeSense — ML Anomaly & Panic Trading Detector Service
Loads trained IsolationForest model from backend/ml/models
and performs anomaly detection on portfolio transactions.
"""
import os
import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[3] / "ml" / "models"

class AnomalyDetectorService:
    def __init__(self):
        self.model = None
        self.features = []
        self.is_loaded = False
        
        self.load_model()
        
    def load_model(self):
        """
        Loads the trained model and feature config from disk.
        """
        model_path = MODELS_DIR / "anomaly_model.pkl"
        config_path = MODELS_DIR / "anomaly_features.json"
        
        if not (model_path.exists() and config_path.exists()):
            logger.warning(
                "Trained IsolationForest model not found in %s. "
                "Detector will use a rule-based fallback.",
                MODELS_DIR
            )
            self.is_loaded = False
            return
            
        try:
            self.model = joblib.load(model_path)
            
            with open(config_path, "r") as f:
                config = json.load(f)
                self.features = config["features"]
                
            self.is_loaded = True
            logger.info("ML Anomaly Detector successfully loaded from %s", MODELS_DIR)
        except Exception as e:
            logger.exception("Failed to load anomaly model from disk. Falling back to heuristic mode: %s", str(e))
            self.is_loaded = False

    def detect_anomalies(self, transactions: list, portfolio_value: float) -> list:
        """
        Detects anomalous trades in a list of transactions.
        
        Args:
            transactions: list of Transaction ORM objects (sorted by trade_date ascending)
            portfolio_value: current total value of the portfolio
            
        Returns:
            A list of dicts representing TradeAnomalyResponse schemas.
        """
        if not transactions or portfolio_value <= 0:
            return []
            
        anomalies = []
        
        # Sort transactions by date and time if available (using created_at as tie-breaker if needed, or assume sorted)
        # We assume transactions are sorted by trade_date for heuristic calculation.
        transactions_sorted = sorted(transactions, key=lambda t: t.trade_date)
        
        last_trade_date = None
        daily_count = 0
        
        df_records = []
        
        for t in transactions_sorted:
            trade_val = float(t.total_value)
            trade_val_pct = trade_val / portfolio_value if portfolio_value > 0 else 0
            
            # Simple simulation of intraday times since we only have trade_date in the MVP
            # We'll use day differences converted to minutes
            if last_trade_date is None:
                mins_since_last = 1440 * 10 # Default to 10 days
            else:
                days_diff = (t.trade_date - last_trade_date).days
                if days_diff == 0:
                    daily_count += 1
                    # Synthesize intraday mins based on how many trades happened today
                    mins_since_last = max(1, 390 // (daily_count + 1)) # 390 mins in a trading day
                else:
                    daily_count = 1
                    mins_since_last = days_diff * 1440
                    
            last_trade_date = t.trade_date
            
            record = {
                "transaction_id": str(t.id),
                "symbol": t.symbol,
                "trade_date": t.trade_date.isoformat(),
                "type": t.transaction_type,
                "trade_value_pct": trade_val_pct,
                "time_since_last_trade_mins": mins_since_last,
                "daily_trade_count": daily_count
            }
            df_records.append(record)
            
        if not df_records:
            return []
            
        if not self.is_loaded:
            # Fallback heuristic
            logger.debug("Anomaly model not loaded. Using fallback.")
            for rec in df_records:
                flags = []
                if rec["trade_value_pct"] > 0.20 and rec["time_since_last_trade_mins"] < 60:
                    flags.append("High Volume Rapid Trade")
                if rec["daily_trade_count"] >= 5:
                    flags.append("High Frequency Trading (Overtrading)")
                    
                if flags:
                    anomalies.append({
                        "transaction_id": rec["transaction_id"],
                        "symbol": rec["symbol"],
                        "trade_date": rec["trade_date"],
                        "type": rec["type"],
                        "anomaly_score": 0.85, # static high score
                        "flags": flags
                    })
            return anomalies
            
        # ML Inference
        df = pd.DataFrame(df_records)
        X = df[self.features]
        
        # predict returns 1 for inliers, -1 for outliers
        preds = self.model.predict(X)
        # decision_function returns anomaly score (lower is more anomalous, typically negative for outliers)
        scores = self.model.decision_function(X)
        
        for idx, (pred, score) in enumerate(zip(preds, scores)):
            if pred == -1:
                rec = df_records[idx]
                flags = []
                
                # Derive human readable flags from features
                if rec["trade_value_pct"] > 0.15:
                    flags.append("Unusually Large Position Size")
                if rec["time_since_last_trade_mins"] < 30:
                    flags.append("Rapid Consecutive Trading")
                if rec["daily_trade_count"] > 4:
                    flags.append("High Frequency Daily Clustering")
                    
                if not flags:
                    flags.append("Atypical Trading Pattern")
                    
                # Normalize score to a 0-1 scale where 1 is highly anomalous
                # decision_function is roughly between -0.5 and +0.5
                normalized_score = float(max(0, min(1, 0.5 - score)))
                
                anomalies.append({
                    "transaction_id": rec["transaction_id"],
                    "symbol": rec["symbol"],
                    "trade_date": rec["trade_date"],
                    "type": rec["type"],
                    "anomaly_score": normalized_score,
                    "flags": flags
                })
                
        # Sort anomalies by score descending
        anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
        return anomalies

# Global singleton
anomaly_detector = AnomalyDetectorService()
