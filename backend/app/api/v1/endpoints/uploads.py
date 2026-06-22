import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.analytics import UploadResponse
from app.services.ingestion import IngestionCoordinator


router = APIRouter(tags=["Uploads"])


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


@router.post(
    "/uploads/csv",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_csv(
    portfolio_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload a transaction statement CSV file (Zerodha or Groww format) for a portfolio.
    Parses transactions, filters duplicates, and updates holdings.
    """
    await _verify_portfolio_owner(portfolio_id, current_user, db)

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported.",
        )

    try:
        content_bytes = await file.read()
        csv_content = content_bytes.decode("utf-8")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read or decode CSV file contents.",
        )

    try:
        stats = await IngestionCoordinator.ingest_csv(db, portfolio_id, csv_content)
        return stats
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during ingestion: {str(e)}",
        )



