"""
TradeSense — Analytics API Endpoints
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.behavioral_metric import BehavioralMetric
from app.models.recommendation import Recommendation
from app.schemas.analytics import BehavioralMetricResponse, RecommendationResponse, MLRiskScoreResponse, PortfolioAnomaliesResponse
from app.services.ml.risk_predictor import risk_predictor


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/behavioral-summary", response_model=BehavioralMetricResponse)
async def get_behavioral_summary(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the most recent behavioral metric snapshot for a given portfolio.
    """
    # Security: Ensure portfolio belongs to user
    stmt_p = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    portfolio = (await db.execute(stmt_p)).scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    stmt = select(BehavioralMetric).where(
        BehavioralMetric.portfolio_id == portfolio_id
    ).order_by(desc(BehavioralMetric.computed_at)).limit(1)
    
    metric = (await db.execute(stmt)).scalar_one_or_none()
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No behavioral metrics found. Please upload a CSV first."
        )

    return metric


@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves all ACTIVE recommendations for the current user.
    """
    stmt = select(Recommendation).where(
        Recommendation.user_id == current_user.id,
        Recommendation.status == "ACTIVE"
    ).order_by(desc(Recommendation.generated_at))
    
    recommendations = (await db.execute(stmt)).scalars().all()
    return recommendations


@router.patch("/recommendations/{recommendation_id}/dismiss", response_model=RecommendationResponse)
async def dismiss_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dismisses an active recommendation so it no longer appears in the dashboard.
    """
    stmt = select(Recommendation).where(
        Recommendation.id == recommendation_id,
        Recommendation.user_id == current_user.id
    )
    rec = (await db.execute(stmt)).scalar_one_or_none()
    
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
        
    if rec.status == "DISMISSED":
        return rec
        
    from datetime import datetime, timezone
    rec.status = "DISMISSED"
    rec.dismissed_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(rec)
    
    return rec


@router.get("/ml-risk-score", response_model=MLRiskScoreResponse)
async def get_ml_risk_score(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the ML-based behavioral risk profile and explainability report for a portfolio.
    """
    # Security: Ensure portfolio belongs to user
    stmt_p = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    portfolio = (await db.execute(stmt_p)).scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    stmt = select(BehavioralMetric).where(
        BehavioralMetric.portfolio_id == portfolio_id
    ).order_by(desc(BehavioralMetric.computed_at)).limit(1)
    
    metric = (await db.execute(stmt)).scalar_one_or_none()
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No behavioral metrics found. Please upload a CSV first."
        )

    # Compute risk profile using the ML Risk Predictor Service
    prediction = risk_predictor.predict(metric)
    
    from datetime import datetime, timezone
    return {
        "portfolio_id": portfolio_id,
        "risk_label": prediction["risk_label"],
        "confidence": prediction["confidence"],
        "shap_explanation": prediction["shap_explanation"],
        "model_version": prediction["model_version"],
        "computed_at": datetime.now(timezone.utc)
    }


@router.get("/{portfolio_id}/anomalies", response_model=PortfolioAnomaliesResponse)
async def get_portfolio_anomalies(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Detects anomalous trades in a portfolio using the IsolationForest ML model.
    """
    # Security: Ensure portfolio belongs to user
    stmt_p = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    portfolio = (await db.execute(stmt_p)).scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    from app.models.transaction import Transaction
    from app.models.holding import Holding
    from app.services.ml.anomaly_detector import anomaly_detector

    # Fetch transactions
    stmt_t = select(Transaction).where(Transaction.portfolio_id == portfolio_id).order_by(Transaction.trade_date)
    transactions = (await db.execute(stmt_t)).scalars().all()

    if not transactions:
        from datetime import datetime, timezone
        return {
            "portfolio_id": portfolio_id,
            "anomalies": [],
            "model_version": getattr(anomaly_detector, "model_version", "isolation-forest-100") if anomaly_detector.is_loaded else "fallback-heuristic-1.0",
            "computed_at": datetime.now(timezone.utc)
        }

    # Fetch holdings to get current portfolio value
    stmt_h = select(Holding).where(Holding.portfolio_id == portfolio_id)
    holdings = (await db.execute(stmt_h)).scalars().all()
    
    from decimal import Decimal
    portfolio_value = sum(float(h.market_value) for h in holdings if h.market_value)
    
    # If no market value (e.g., all sold), fallback to sum of buys
    if portfolio_value <= 0:
        portfolio_value = sum(float(t.total_value) for t in transactions if t.transaction_type == 'BUY')
        
    anomalies = anomaly_detector.detect_anomalies(transactions, portfolio_value)
    
    from datetime import datetime, timezone
    return {
        "portfolio_id": portfolio_id,
        "anomalies": anomalies,
        "model_version": "isolation-forest-100" if anomaly_detector.is_loaded else "fallback-heuristic-1.0",
        "computed_at": datetime.now(timezone.utc)
    }
