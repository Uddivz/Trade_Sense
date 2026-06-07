"""
TradeSense — Holding ORM Model
Represents the current open position in a portfolio for a given symbol.
Recomputed after every CSV upload via the holdings service.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    exchange: Mapped[str] = mapped_column(String(20), default="NSE")
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)

    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    avg_cost_basis: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    current_value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    unrealized_pnl_pct: Mapped[float] = mapped_column(Numeric(10, 6), default=0)

    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="holdings")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Holding {self.symbol} qty={self.quantity} cost={self.avg_cost_basis}>"
