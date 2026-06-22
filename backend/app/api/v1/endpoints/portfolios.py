"""
TradeSense — Portfolio Endpoints
Implements CRUD routes for portfolio management.
"""
import math
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.models.transaction import Transaction
from app.models.holding import Holding
from app.schemas.portfolio import PortfolioCreate, PortfolioResponse
from app.schemas.transaction import PaginatedResponse, TransactionResponse
from app.schemas.holding import HoldingResponse

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


async def _verify_portfolio_owner(
    portfolio_id: uuid.UUID, current_user: User, db: AsyncSession
) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalars().first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or unauthorized.",
        )
    return portfolio


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


@router.get(
    "/{portfolio_id}/transactions",
    response_model=PaginatedResponse[TransactionResponse],
)
async def get_portfolio_transactions(
    portfolio_id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=50, ge=1, le=200, description="Rows per page (max 200)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TransactionResponse]:
    """
    Retrieve paginated transactions for a portfolio, ordered by trade_date DESC.

    - **page**: page number starting at 1
    - **page_size**: number of records per page (1–200, default 50)

    Returns a paginated envelope with `items`, `total`, `page`, `page_size`, and `total_pages`.
    """
    await _verify_portfolio_owner(portfolio_id, current_user, db)

    base_where = Transaction.portfolio_id == portfolio_id

    # Total count (single scalar query — does not load rows)
    count_result = await db.execute(
        select(func.count()).select_from(Transaction).where(base_where)
    )
    total: int = count_result.scalar_one()

    # Paginated rows
    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(Transaction)
        .where(base_where)
        .order_by(Transaction.trade_date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(rows_result.scalars().all())

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
async def get_portfolio_holdings(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Holding]:
    """
    Retrieve all current holdings for a portfolio.
    """
    await _verify_portfolio_owner(portfolio_id, current_user, db)

    result = await db.execute(
        select(Holding)
        .where(Holding.portfolio_id == portfolio_id)
        .order_by(Holding.market_value.desc())
    )
    return list(result.scalars().all())
