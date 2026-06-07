"""
TradeSense — Portfolio ORM Model
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    broker_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    broker_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    cost_basis_method: Mapped[str] = mapped_column(String(20), default="FIFO")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolios")  # type: ignore[name-defined]
    transactions: Mapped[list["Transaction"]] = relationship(  # type: ignore[name-defined]
        "Transaction", back_populates="portfolio", cascade="all, delete-orphan"
    )
    holdings: Mapped[list["Holding"]] = relationship(  # type: ignore[name-defined]
        "Holding", back_populates="portfolio", cascade="all, delete-orphan"
    )
    behavioral_metrics: Mapped[list["BehavioralMetric"]] = relationship(  # type: ignore[name-defined]
        "BehavioralMetric", back_populates="portfolio", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} name={self.name}>"
