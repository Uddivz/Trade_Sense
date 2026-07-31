import pytest
from app.services.ml.risk_predictor import risk_predictor, RiskPredictorService
from app.models.behavioral_metric import BehavioralMetric

def test_risk_predictor_heuristic_fallback():
    # Force is_loaded = False to test fallback
    predictor = RiskPredictorService()
    predictor.is_loaded = False
    
    # Mock behavioral metric
    metric = BehavioralMetric(
        pgr=0.6,
        plr=0.2,
        disposition_effect_score=0.4,
        hhi=3000.0,
        portfolio_turnover_ratio=0.15,
        cost_drag_pct=0.01
    )
    
    result = predictor.predict(metric)
    
    assert "risk_label" in result
    assert result["risk_label"] in ["LOW", "MEDIUM", "HIGH"]
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert "shap_explanation" in result
    assert len(result["shap_explanation"]) > 0
    assert "model_version" in result
    assert "fallback" in result["model_version"]

def test_risk_predictor_empty_metrics():
    predictor = RiskPredictorService()
    predictor.is_loaded = False
    
    # Test with dictionary
    metrics_dict = {
        "pgr": 0.0,
        "plr": 0.0,
        "disposition_effect_score": 0.0,
        "hhi": 0.0,
        "portfolio_turnover_ratio": 0.0,
        "cost_drag_pct": 0.0
    }
    
    result = predictor.predict(metrics_dict)
    assert result["risk_label"] == "LOW"
    assert result["confidence"] > 0.8
