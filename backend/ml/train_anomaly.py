"""
TradeSense ML — Unsupervised Anomaly & Panic Trading Detector
Trains an IsolationForest model on synthetic transaction data.
"""
import json
import joblib
import pandas as pd
import numpy as np
import random
from pathlib import Path
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def generate_synthetic_transactions(num_portfolios=50, days=365):
    """
    Generate synthetic transactions with normal trading patterns and injected anomalies.
    Features:
    - trade_value_pct: ratio of trade value to total portfolio value (approx)
    - time_since_last_trade_mins: minutes since last trade in the portfolio
    - daily_trade_count: cumulative count of trades on the same day for the portfolio
    """
    records = []
    
    for _ in range(num_portfolios):
        portfolio_value = random.uniform(100000, 1000000)
        start_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 100))
        current_date = start_date
        
        last_trade_time = None
        
        for day in range(days):
            # Normal day: 0 to 3 trades
            if random.random() < 0.2: # 20% chance of trading on a given day
                num_trades = random.randint(1, 3)
                daily_count = 0
                
                # Check for anomaly injection
                is_anomaly = random.random() < 0.05 # 5% chance of anomalous day
                
                if is_anomaly:
                    # Panic selling / Revenge trading: high frequency, big volume
                    num_trades = random.randint(5, 12)
                
                for t in range(num_trades):
                    daily_count += 1
                    
                    if is_anomaly:
                        # Anomalous trade: very close in time, huge chunk of portfolio
                        trade_val_pct = random.uniform(0.15, 0.40) # 15-40% of portfolio
                        mins_since_last = random.randint(1, 15) # panic trades happen fast
                    else:
                        # Normal trade
                        trade_val_pct = random.uniform(0.01, 0.10) # 1-10% of portfolio
                        if last_trade_time is None:
                            mins_since_last = 1440 * random.randint(1, 30) # days apart
                        else:
                            mins_since_last = random.randint(60, 1440 * 5) # hours/days apart
                    
                    # Update timestamps
                    if last_trade_time is None:
                        trade_time = current_date + timedelta(hours=random.randint(9, 15))
                    else:
                        trade_time = last_trade_time + timedelta(minutes=mins_since_last)
                    
                    last_trade_time = trade_time
                    
                    records.append({
                        "trade_value_pct": trade_val_pct,
                        "time_since_last_trade_mins": mins_since_last,
                        "daily_trade_count": daily_count,
                        "is_anomaly": 1 if is_anomaly else 0  # For evaluation only
                    })
                    
            current_date += timedelta(days=1)
            
    return pd.DataFrame(records)

def train_anomaly_model():
    print("Generating synthetic transaction data for anomaly detection...")
    df = generate_synthetic_transactions()
    
    features = ["trade_value_pct", "time_since_last_trade_mins", "daily_trade_count"]
    X = df[features]
    
    print(f"Dataset shape: {X.shape}")
    print(f"Injected anomalies: {df['is_anomaly'].sum()} ({(df['is_anomaly'].sum() / len(df)) * 100:.2f}%)")
    
    # Isolation Forest
    # contamination = expected proportion of outliers. We estimate ~3-5% based on our generation.
    model = IsolationForest(
        n_estimators=100,
        max_samples='auto',
        contamination=0.05,
        random_state=42
    )
    
    print("Training IsolationForest model...")
    model.fit(X)
    
    # Evaluate internally
    df['pred'] = model.predict(X)
    # IsolationForest outputs -1 for outliers and 1 for inliers
    df['is_outlier_pred'] = (df['pred'] == -1).astype(int)
    
    match = (df['is_anomaly'] == df['is_outlier_pred']).mean()
    print(f"Heuristic synthetic match rate: {match:.2%}")
    
    # Save model and config
    model_path = MODELS_DIR / "anomaly_model.pkl"
    config_path = MODELS_DIR / "anomaly_features.json"
    
    joblib.dump(model, model_path)
    
    with open(config_path, "w") as f:
        json.dump({
            "features": features,
            "version": "isolation-forest-100"
        }, f, indent=4)
        
    print(f"Model saved to {model_path}")
    print("Anomaly Detection pipeline complete.")

if __name__ == "__main__":
    train_anomaly_model()
