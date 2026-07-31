"""
TradeSense — ML Risk Predictor Service
Loads trained XGBoost model and SHAP explainer from backend/ml/models
and performs behavioral risk classification and explainability.
Resilient to missing SHAP library.
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

# Check if shap is installed
try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    logger.info("SHAP package is not installed. Predictor will fallback to feature-importance explanations.")

class RiskPredictorService:
    def __init__(self):
        self.model = None
        self.explainer = None
        self.features = []
        self.label_map = {}
        self.inv_label_map = {}
        self.is_loaded = False
        self.has_shap_artifact = False
        
        self.load_model()
        
    def load_model(self):
        """
        Loads the trained model, explainer, and feature config from disk.
        """
        model_path = MODELS_DIR / "risk_model.pkl"
        explainer_path = MODELS_DIR / "shap_explainer.pkl"
        config_path = MODELS_DIR / "feature_names.json"
        
        if not (model_path.exists() and config_path.exists()):
            logger.warning(
                "Trained XGBoost models not found in %s. "
                "FastAPI will use a rule-based fallback predictor until `python -m ml.train` is run.",
                MODELS_DIR
            )
            self.is_loaded = False
            return
            
        try:
            self.model = joblib.load(model_path)
            
            with open(config_path, "r") as f:
                config = json.load(f)
                self.features = config["features"]
                self.inv_label_map = {int(k): v for k, v in config["inv_label_map"].items()}
                self.has_shap_artifact = config.get("has_shap", False)
                
            if HAS_SHAP and self.has_shap_artifact and explainer_path.exists():
                try:
                    self.explainer = joblib.load(explainer_path)
                except Exception as e:
                    logger.warning("Could not load SHAP explainer artifact: %s. Using feature importance fallback.", str(e))
                    self.explainer = None
            else:
                self.explainer = None
                
            self.is_loaded = True
            logger.info("ML Risk Profiler models successfully loaded from %s (SHAP available: %s)", MODELS_DIR, self.explainer is not None)
        except Exception as e:
            logger.exception("Failed to load ML models from disk. Falling back to heuristic mode: %s", str(e))
            self.is_loaded = False

    def predict(self, metrics) -> dict:
        """
        Predicts investor risk profile and returns class probabilities and explanations.
        
        Args:
            metrics: An object or dict containing:
                pgr, plr, disposition_effect_score, hhi, portfolio_turnover_ratio, cost_drag_pct
                
        Returns:
            A dictionary matching MLRiskScoreResponse.
        """
        def get_val(key):
            if isinstance(metrics, dict):
                return metrics.get(key, 0.0)
            return getattr(metrics, key, 0.0) or 0.0
            
        pgr = get_val("pgr")
        plr = get_val("plr")
        de_score = get_val("disposition_effect_score")
        hhi = get_val("hhi")
        ptr = get_val("portfolio_turnover_ratio")
        cost_drag = get_val("cost_drag_pct")
        
        if not self.is_loaded:
            # Fallback rule-based heuristic prediction if no ML model is trained
            logger.debug("ML models not loaded. Using rule-based fallback prediction.")
            score = float(de_score) * 1.5 + float(hhi) / 5000.0 + float(ptr) * 2.0
            
            if score > 1.2:
                risk_label = "HIGH"
                confidence = 0.85
            elif score > 0.4:
                risk_label = "MEDIUM"
                confidence = 0.70
            else:
                risk_label = "LOW"
                confidence = 0.90
                
            contributions = [
                {
                    "feature": "disposition_effect_score",
                    "value": float(de_score),
                    "shap_value": float(de_score) * 0.4,
                    "direction": "increases_risk" if de_score > 0.05 else "reduces_risk"
                },
                {
                    "feature": "hhi",
                    "value": float(hhi),
                    "shap_value": (float(hhi) - 1500) / 10000.0,
                    "direction": "increases_risk" if hhi > 2500 else "reduces_risk"
                },
                {
                    "feature": "portfolio_turnover_ratio",
                    "value": float(ptr),
                    "shap_value": float(ptr) * 0.5,
                    "direction": "increases_risk" if ptr > 0.10 else "reduces_risk"
                },
                {
                    "feature": "cost_drag_pct",
                    "value": float(cost_drag),
                    "shap_value": float(cost_drag) * 0.2,
                    "direction": "increases_risk" if cost_drag > 0.02 else "reduces_risk"
                }
            ]
            
            contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            
            return {
                "risk_label": risk_label,
                "confidence": confidence,
                "shap_explanation": contributions,
                "model_version": "fallback-heuristic-1.0"
            }
            
        # ML Inference
        input_data = pd.DataFrame([{
            "pgr": float(pgr),
            "plr": float(plr),
            "disposition_effect_score": float(de_score),
            "hhi": float(hhi),
            "portfolio_turnover_ratio": float(ptr),
            "cost_drag_pct": float(cost_drag)
        }])
        
        pred_class = int(self.model.predict(input_data)[0])
        pred_prob = self.model.predict_proba(input_data)[0]
        
        risk_label = self.inv_label_map.get(pred_class, "MEDIUM")
        confidence = float(pred_prob[pred_class])
        
        contributions = []
        
        # 1. Try SHAP explanation if explainer is active
        if self.explainer is not None:
            try:
                shap_vals = self.explainer.shap_values(input_data)
                
                if isinstance(shap_vals, list):
                    class_shap_vals = shap_vals[pred_class][0]
                else:
                    class_shap_vals = shap_vals[0, :, pred_class] if len(shap_vals.shape) == 3 else shap_vals[0]
                    
                for i, feat_name in enumerate(self.features):
                    shap_val = float(class_shap_vals[i])
                    feat_val = float(input_data.iloc[0][feat_name])
                    direction = "increases_risk" if shap_val > 0 else "reduces_risk"
                    
                    contributions.append({
                        "feature": feat_name,
                        "value": feat_val,
                        "shap_value": shap_val,
                        "direction": direction
                    })
            except Exception as e:
                logger.warning("Error computing SHAP values: %s. Falling back to feature importance.", str(e))
                contributions = []
                
        # 2. Fallback to model feature importances if SHAP failed or is unavailable
        if not contributions:
            importances = self.model.feature_importances_
            for i, feat_name in enumerate(self.features):
                feat_val = float(input_data.iloc[0][feat_name])
                importance = float(importances[i])
                
                # Heuristic mapping for feature importance directions
                if feat_name in ["disposition_effect_score", "hhi", "portfolio_turnover_ratio", "cost_drag_pct"]:
                    direction = "increases_risk" if feat_val > 0.1 or (feat_name == "hhi" and feat_val > 1500) else "reduces_risk"
                else:
                    direction = "reduces_risk" if feat_val > 0.5 else "increases_risk"
                    
                # Estimate a SHAP-like value from model importance & feature value scale
                if feat_name == "hhi":
                    scaled_val = feat_val / 10000.0
                else:
                    scaled_val = feat_val
                shap_val = importance * (scaled_val if direction == "increases_risk" else -scaled_val)
                
                contributions.append({
                    "feature": feat_name,
                    "value": feat_val,
                    "shap_value": shap_val,
                    "direction": direction
                })
                
        # Sort by absolute contribution strength
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        
        return {
            "risk_label": risk_label,
            "confidence": confidence,
            "shap_explanation": contributions,
            "model_version": f"xgboost-{getattr(self.model, 'n_estimators', 100)}"
        }

# Global singleton service instance
risk_predictor = RiskPredictorService()
