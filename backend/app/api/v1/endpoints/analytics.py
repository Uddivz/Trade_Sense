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
from app.schemas.analytics import BehavioralMetricResponse, RecommendationResponse


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
