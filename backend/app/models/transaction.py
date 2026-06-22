"""
TradeSense — Transaction ORM Model
Represents a single buy or sell event in a portfolio.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "external_trade_id", name="uix_portfolio_external_trade_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Broker-assigned trade ID — used for deduplication
    broker_trade_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_trade_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True)

    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    exchange: Mapped[str] = mapped_column(String(20), default="NSE")
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY | SELL

    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    total_value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)

    brokerage: Mapped[float] = mapped_column(Numeric(12, 4), default=0)
    stt: Mapped[float] = mapped_column(Numeric(12, 4), default=0)
    other_charges: Mapped[float] = mapped_column(Numeric(12, 4), default=0)
    fees: Mapped[float] = mapped_column(Numeric(12, 4), default=0)
    net_value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="transactions")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type} {self.symbol} x{self.quantity} @ {self.price}>"
