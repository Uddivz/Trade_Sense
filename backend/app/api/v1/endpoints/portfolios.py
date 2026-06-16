"""
TradeSense — Portfolio Endpoints
Implements CRUD routes for portfolio management.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioResponse

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_in: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Portfolio:
    """
    Create a new portfolio for the authenticated user.
    If it is the user's first portfolio, it is automatically marked as the default.
    """
    # Check if user already has any portfolios
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    has_portfolios = result.scalars().first() is not None
    is_default = not has_portfolios

    new_portfolio = Portfolio(
        user_id=current_user.id,
        name=portfolio_in.name,
        broker_name=portfolio_in.broker_name,
        currency=portfolio_in.currency,
        cost_basis_method=portfolio_in.cost_basis_method,
        is_default=is_default,
    )
    db.add(new_portfolio)
    await db.commit()
    await db.refresh(new_portfolio)
    return new_portfolio


@router.get("/", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[Portfolio]:
    """
    List all portfolios belonging to the authenticated user.
    """
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == current_user.id)
        .order_by(Portfolio.created_at.desc())
    )
    portfolios = result.scalars().all()
    return list(portfolios)
