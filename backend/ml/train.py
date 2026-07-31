"""
TradeSense ML — XGBoost Risk Profiler Model Training Pipeline
Resilient to missing packages (mlflow, shap) for offline/restricted environments.
"""
import os
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

import xgboost as xgb
from ml.data_prep import prepare_dataset

# Optional imports
try:
    import mlflow
    import mlflow.xgboost
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    print("MLflow is not installed. Experiment tracking will be logged to stdout.")

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    print("SHAP is not installed. Model explanation will fallback to built-in feature importances.")

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def train_risk_model(num_samples=400):
    """
    Simulates portfolio transactions, computes features, trains an XGBoost classifier,
    logs results to MLflow (if available), builds a SHAP explainer (if available),
    and saves the serialized models.
    """
    # 1. Prepare data
    df = prepare_dataset(num_samples)
    
    # Define features and label
    features = [
        "pgr", 
        "plr", 
        "disposition_effect_score", 
        "hhi", 
        "portfolio_turnover_ratio", 
        "cost_drag_pct"
    ]
    
    X = df[features]
    
    # Map target label string to numeric class integers: LOW=0, MEDIUM=1, HIGH=2
    label_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    inv_label_map = {v: k for k, v in label_map.items()}
    y = df["risk_label"].map(label_map)
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # Model parameters
    params = {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "mlogloss",
        "objective": "multi:softprob"
    }

    # 2. Train Model
    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, 
        y_train, 
        eval_set=[(X_test, y_test)], 
        verbose=False
    )
    
    # 3. Evaluate model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Test Accuracy: {accuracy:.4f}")
    
    report = classification_report(
        y_test, y_pred, target_names=list(label_map.keys()), output_dict=True
    )
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=list(label_map.keys())))

    # 4. Save model and metadata locally
    model_path = MODELS_DIR / "risk_model.pkl"
    explainer_path = MODELS_DIR / "shap_explainer.pkl"
    feature_names_path = MODELS_DIR / "feature_names.json"
    
    joblib.dump(model, model_path)
    
    # Save SHAP explainer only if available, otherwise write None or clean file
    if HAS_SHAP:
        try:
            explainer = shap.TreeExplainer(model)
            joblib.dump(explainer, explainer_path)
            print("SHAP explainer successfully built and saved.")
        except Exception as e:
            print(f"Error building SHAP explainer: {e}")
            if explainer_path.exists():
                os.remove(explainer_path)
    else:
        # If no SHAP, delete any old explainer so we don't load stale artifacts
        if explainer_path.exists():
            os.remove(explainer_path)
            
    with open(feature_names_path, "w") as f:
        json.dump({
            "features": features,
            "label_map": label_map,
            "inv_label_map": inv_label_map,
            "has_shap": HAS_SHAP
        }, f, indent=4)
        
    print(f"Model successfully saved to {MODELS_DIR}")

    # 5. Log to MLflow if available
    if HAS_MLFLOW:
        try:
            mlflow.set_experiment("tradesense_risk_profiling")
            with mlflow.start_run() as run:
                print(f"Logging to MLflow Run: {run.info.run_id}")
                mlflow.log_params(params)
                mlflow.log_metric("accuracy", accuracy)
                for class_name, metrics in report.items():
                    if isinstance(metrics, dict):
                        for metric_name, val in metrics.items():
                            mlflow.log_metric(f"{class_name}_{metric_name}", val)
                            
                mlflow.log_artifact(str(model_path))
                mlflow.log_artifact(str(feature_names_path))
                if HAS_SHAP and explainer_path.exists():
                    mlflow.log_artifact(str(explainer_path))
                mlflow.xgboost.log_model(model, artifact_path="model")
        except Exception as e:
            print(f"Failed to log to MLflow: {e}")
            
    return accuracy

if __name__ == "__main__":
    train_risk_model()
