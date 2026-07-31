"""
TradeSense ML — Data Preparation and Portfolio Simulation
Loads Kaggle BSE/NSE stock CSVs, simulates trading behavior,
and generates behavioral features for model training.
"""
import os
import random
import numpy as np
import pandas as pd
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# Import pure math logic from TradeSense app
from app.services.analytics.math import (
    calculate_pgr,
    calculate_plr,
    calculate_disposition_effect,
    calculate_hhi,
    calculate_ptr,
    calculate_cost_drag
)

DATA_DIR = Path(__file__).parent / "data"

def generate_synthetic_stock_prices(num_stocks=10, num_days=500):
    """
    Generates synthetic BSE/NSE style stock price CSVs to ensure the pipeline
    runs out of the box when Kaggle datasets are not manually dropped in.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "ITC", "LT", "SBIN", "BHARTIARTL", "KOTAKBANK"]
    start_date = datetime(2024, 1, 1)
    
    print(f"Generating synthetic stock price data for {len(symbols)} symbols in {DATA_DIR}...")
    
    for sym in symbols[:num_stocks]:
        dates = [start_date + timedelta(days=i) for i in range(num_days)]
        
        # Simulate stock price drift
        price = random.uniform(100, 3000)
        prices = []
        volumes = []
        for _ in range(num_days):
            price = price * (1 + random.uniform(-0.03, 0.035)) # slight upward bias
            price = max(price, 5.0)
            prices.append(round(price, 2))
            volumes.append(random.randint(10000, 5000000))
            
        df = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Symbol": sym,
            "Close": prices,
            "Open": [round(p * random.uniform(0.98, 1.02), 2) for p in prices],
            "High": [round(p * random.uniform(1.0, 1.04), 2) for p in prices],
            "Low": [round(p * random.uniform(0.96, 1.0), 2) for p in prices],
            "Volume": volumes
        })
        
        df.to_csv(DATA_DIR / f"{sym}.csv", index=False)
    print("Synthetic price data generation complete.")

def load_stock_data():
    """
    Loads stock price CSV files from backend/ml/data/ directory.
    Supports two formats:
      1. Consolidated CSV (e.g. NIFTY50_all.csv) with a 'Symbol' column — splits into per-symbol DataFrames.
      2. Individual per-stock CSVs (e.g. RELIANCE.csv, TCS.csv) — loaded directly.
    Falls back to generating synthetic stock price data if none found.
    """
    if not DATA_DIR.exists() or len(list(DATA_DIR.glob("*.csv"))) == 0:
        generate_synthetic_stock_prices()
        
    stock_files = list(DATA_DIR.glob("*.csv"))
    all_data = {}
    
    for file_path in stock_files:
        try:
            df = pd.read_csv(file_path)
            # Standardize column names to Title Case
            df.columns = [c.strip().title() for c in df.columns]
            
            # --- Format 1: Consolidated multi-symbol CSV (e.g. NIFTY50_all.csv) ---
            if "Symbol" in df.columns and "Date" in df.columns and "Close" in df.columns:
                # Check if this is truly a multi-symbol file
                unique_symbols = df["Symbol"].nunique()
                if unique_symbols > 1:
                    print(f"Loading consolidated dataset: {file_path.name} ({len(df)} rows, {unique_symbols} symbols)")
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                    df = df.dropna(subset=["Date", "Close"])
                    
                    for sym, sym_df in df.groupby("Symbol"):
                        sym_df = sym_df.sort_values("Date").reset_index(drop=True)
                        # Only include stocks with enough history (at least 100 trading days)
                        if len(sym_df) >= 100:
                            all_data[sym] = sym_df[["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]].copy()
                    print(f"  Extracted {len(all_data)} symbols with 100+ days of history")
                    continue
                    
            # --- Format 2: Individual per-stock CSV (e.g. RELIANCE.csv) ---
            symbol = file_path.stem
            if "Date" in df.columns and "Close" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.dropna(subset=["Date", "Close"])
                df = df.sort_values("Date").reset_index(drop=True)
                if len(df) >= 100:
                    all_data[symbol] = df
                    
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            
    print(f"Total symbols loaded: {len(all_data)}")
    return all_data


def get_stock_row_on_or_after(stock_sym_data, target_date):
    """
    Uses binary search to find the first stock row on or after the target_date.
    Extremely fast compared to boolean masking and Pandas Series instantiation.
    """
    dates = stock_sym_data["dates"]
    target_np = np.datetime64(target_date)
    idx = np.searchsorted(dates, target_np)
    if idx >= len(dates):
        return None
    date_str = str(dates[idx])[:10]
    return {
        "Close": float(stock_sym_data["close"][idx]),
        "DateStr": date_str,
        "Open": float(stock_sym_data["open"][idx]),
        "High": float(stock_sym_data["high"][idx]),
        "Low": float(stock_sym_data["low"][idx]),
        "Volume": float(stock_sym_data["volume"][idx])
    }


def simulate_investor_portfolio(stock_data, investor_id):
    """
    Simulates transaction history and current holdings for a single investor
    using historical stock price movements. Returns computed behavioral metrics.
    
    Each investor gets a randomized 'personality' archetype that controls
    trading frequency, sell bias, and position sizing — producing diverse
    behavioral feature distributions.
    """
    symbols = list(stock_data.keys())
    if not symbols:
        return None
    
    # --- Investor Personality (randomized per investor) ---
    disposition_bias = random.uniform(0.0, 0.8)
    trade_frequency = random.uniform(0.02, 0.40)
    sell_fraction_range = (random.uniform(0.2, 0.5), random.uniform(0.6, 1.0))
    num_assets = random.randint(2, min(8, len(symbols)))
    
    portfolio_symbols = random.sample(symbols, num_assets)
    
    transactions = []
    holdings = {}
    
    # Time window: limit to max 2 years (730 days) to represent realistic retail behavior
    min_date = min(stock_data[sym]["min_date"] for sym in portfolio_symbols)
    max_date = max(stock_data[sym]["max_date"] for sym in portfolio_symbols)
    time_delta = max_date - min_date
    
    if time_delta.days > 730:
        max_start = time_delta.days - 730
        start_offset = random.randint(0, max_start)
        investor_start = min_date + timedelta(days=start_offset)
        investor_end = investor_start + timedelta(days=730)
    else:
        start_offset = random.randint(0, int(time_delta.days * 0.4))
        end_offset = random.randint(0, int(time_delta.days * 0.2))
        investor_start = min_date + timedelta(days=start_offset)
        investor_end = max_date - timedelta(days=end_offset)
    
    realized_gains = Decimal("0.0")
    realized_losses = Decimal("0.0")
    
    current_date = investor_start
    capital = random.uniform(50000, 500000)
    
    # Buy initial stocks
    for sym in portfolio_symbols:
        sym_data = stock_data[sym]
        row = get_stock_row_on_or_after(sym_data, current_date)
        if row is None:
            continue
        price = row["Close"]
        if price <= 0:
            continue
        date_str = row["DateStr"]
        
        allocation = capital * random.uniform(0.08, 0.35)
        qty = int(allocation // price)
        if qty <= 0:
            continue
            
        cost = qty * price
        capital -= cost
        
        brokerage = cost * 0.0005
        stt = cost * 0.001
        fees = 20.0
        other = cost * 0.0001
        
        transactions.append({
            "symbol": sym, "type": "BUY", "quantity": qty, "price": price,
            "date": date_str, "brokerage": brokerage, "stt": stt,
            "fees": fees, "other": other, "value": cost
        })
        
        holdings[sym] = {"qty": qty, "buy_price": price, "current_price": price}
        
    # Simulate trading behavior over the period
    current_date += timedelta(days=random.randint(10, 30))
    while current_date < investor_end:
        for sym in list(holdings.keys()):
            sym_data = stock_data[sym]
            row = get_stock_row_on_or_after(sym_data, current_date)
            if row is None:
                continue
            price = row["Close"]
            if price <= 0:
                continue
            date_str = row["DateStr"]
            
            holdings[sym]["current_price"] = price
            
            buy_price = holdings[sym]["buy_price"]
            if buy_price <= 0:
                continue
            pnl_pct = (price - buy_price) / buy_price
            
            sell_prob = trade_frequency * 0.5
            if pnl_pct > 0.05:
                sell_prob += disposition_bias * 0.3
            elif pnl_pct < -0.05:
                sell_prob -= disposition_bias * 0.15
                
            sell_prob = max(0.01, min(0.6, sell_prob))
            
            if random.random() < sell_prob:
                fraction = random.uniform(*sell_fraction_range)
                qty_to_sell = max(1, int(holdings[sym]["qty"] * fraction))
                qty_to_sell = min(qty_to_sell, holdings[sym]["qty"])
                
                val = qty_to_sell * price
                capital += val
                
                brokerage = val * 0.0005
                stt = val * 0.001
                fees = 20.0
                other = val * 0.0001
                
                transactions.append({
                    "symbol": sym, "type": "SELL", "quantity": qty_to_sell,
                    "price": price, "date": date_str, "brokerage": brokerage,
                    "stt": stt, "fees": fees, "other": other, "value": val
                })
                
                realized_pnl = qty_to_sell * (price - buy_price)
                if realized_pnl > 0:
                    realized_gains += Decimal(str(realized_pnl))
                else:
                    realized_losses += Decimal(str(abs(realized_pnl)))
                
                holdings[sym]["qty"] -= qty_to_sell
                if holdings[sym]["qty"] <= 0:
                    del holdings[sym]
                    
            elif random.random() < trade_frequency * 0.3 and capital > 5000:
                buy_sym = random.choice(symbols)
                sym_data_b = stock_data[buy_sym]
                b_row = get_stock_row_on_or_after(sym_data_b, current_date)
                if b_row is not None:
                    b_price = b_row["Close"]
                    if b_price > 0:
                        b_qty = int((capital * random.uniform(0.1, 0.35)) // b_price)
                        if b_qty > 0:
                            b_val = b_qty * b_price
                            capital -= b_val
                            
                            transactions.append({
                                "symbol": buy_sym, "type": "BUY", "quantity": b_qty,
                                "price": b_price, "date": b_row["DateStr"],
                                "brokerage": b_val * 0.0005, "stt": b_val * 0.001,
                                "fees": 20.0, "other": b_val * 0.0001, "value": b_val
                            })
                            
                            if buy_sym in holdings:
                                old_qty = holdings[buy_sym]["qty"]
                                old_price = holdings[buy_sym]["buy_price"]
                                new_qty = old_qty + b_qty
                                new_price = ((old_qty * old_price) + (b_qty * b_price)) / new_qty
                                holdings[buy_sym]["qty"] = new_qty
                                holdings[buy_sym]["buy_price"] = new_price
                            else:
                                holdings[buy_sym] = {
                                    "qty": b_qty, "buy_price": b_price, "current_price": b_price
                                }
                            
        current_date += timedelta(days=random.randint(5, 15))
        
    paper_gains = Decimal("0.0")
    paper_losses = Decimal("0.0")
    market_values = []
    
    for sym, hold in holdings.items():
        mv = hold["qty"] * hold["current_price"]
        market_values.append(Decimal(str(mv)))
        unrealized = hold["qty"] * (hold["current_price"] - hold["buy_price"])
        if unrealized > 0:
            paper_gains += Decimal(str(unrealized))
        else:
            paper_losses += Decimal(str(abs(unrealized)))
            
    pgr = calculate_pgr(realized_gains, paper_gains)
    plr = calculate_plr(realized_losses, paper_losses)
    de_score = calculate_disposition_effect(pgr, plr)
    hhi_score = calculate_hhi(market_values)
    
    total_buys = sum(Decimal(str(t["value"])) for t in transactions if t["type"] == "BUY")
    total_sells = sum(Decimal(str(t["value"])) for t in transactions if t["type"] == "SELL")
    total_costs = sum(Decimal(str(t["brokerage"] + t["stt"] + t["fees"] + t["other"])) for t in transactions)
    total_traded_value = sum(Decimal(str(t["value"])) for t in transactions)
    
    current_portfolio_value = sum(market_values)
    ptr_score = calculate_ptr(total_buys, total_sells, current_portfolio_value)
    cost_drag_pct = calculate_cost_drag(total_costs, total_traded_value)
    
    ptr_capped = min(float(ptr_score), 5.0)
    
    score_metric = float(de_score) * 1.0 + float(hhi_score) / 10000.0 + ptr_capped * 0.3
    score_metric += random.normalvariate(0, 0.08)
    
    if score_metric > 1.0:
        risk_label = "HIGH"
    elif score_metric > 0.6:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"
        
    return {
        "pgr": float(pgr),
        "plr": float(plr),
        "disposition_effect_score": float(de_score),
        "hhi": float(hhi_score),
        "portfolio_turnover_ratio": ptr_capped,
        "cost_drag_pct": float(cost_drag_pct),
        "risk_label": risk_label
    }


def prepare_dataset(num_investors=200):
    """
    Runs the portfolio simulation for N investors and returns features and labels
    as a pandas DataFrame ready for XGBoost.
    """
    raw_stock_data = load_stock_data()
    
    # Pre-extract numpy arrays for maximum simulation speed (removes pandas dataframe lookup overhead)
    stock_data = {}
    for sym, df in raw_stock_data.items():
        stock_data[sym] = {
            "dates": df["Date"].values,
            "close": df["Close"].values,
            "open": df["Open"].values if "Open" in df.columns else df["Close"].values,
            "high": df["High"].values if "High" in df.columns else df["Close"].values,
            "low": df["Low"].values if "Low" in df.columns else df["Close"].values,
            "volume": df["Volume"].values if "Volume" in df.columns else np.zeros(len(df)),
            "min_date": df["Date"].min(),
            "max_date": df["Date"].max()
        }
        
    print(f"Loaded stock price data for {len(stock_data)} symbols. Simulating {num_investors} investor behaviors...")
    
    records = []
    for i in range(num_investors):
        res = simulate_investor_portfolio(stock_data, i)
        if res:
            records.append(res)
            
    df = pd.DataFrame(records)
    print(f"Simulation completed. Generated {len(df)} samples.")
    print(df["risk_label"].value_counts())
    
    return df


if __name__ == "__main__":
    df = prepare_dataset(10)
    print(df.head())
