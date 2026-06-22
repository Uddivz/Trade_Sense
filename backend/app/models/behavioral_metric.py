"""
TradeSense — Behavioral Metric ORM Model
Stores computed behavioral analytics for a user/portfolio per time period.
Recomputed by the AnalyticsEngine after every CSV upload.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BehavioralMetric(Base):
    __tablename__ = "behavioral_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    period_type: Mapped[str] = mapped_column(
        String(20), default="ALL_TIME"
    )  # ALL_TIME | MONTHLY | QUARTERLY

    # ── Disposition Effect ──────────────────────────────────────────────
    pgr: Mapped[float | None] = mapped_column(Numeric(6, 5), nullable=True)
    plr: Mapped[float | None] = mapped_column(Numeric(6, 5), nullable=True)
    disposition_effect_score: Mapped[float | None] = mapped_column(Numeric(7, 5), nullable=True)

    # ── Overtrading ─────────────────────────────────────────────────────
    portfolio_turnover_ratio: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    avg_hold_duration_days: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    trade_frequency_per_month: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    cost_drag_pct: Mapped[float | None] = mapped_column(Numeric(7, 5), nullable=True)

    # ── Concentration ───────────────────────────────────────────────────
    # BUG-03 FIX: HHI ranges 0–10,000. Numeric(6,5) max is 9.99999 → overflow.
    # Numeric(10, 4) supports values up to 999999.9999 — covers full HHI range.
    hhi: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # ── Composite Risk Score ────────────────────────────────────────────
    behavioral_risk_score: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)

    # Full metric breakdown (JSON) — consumed directly by the frontend
    metric_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="behavioral_metrics")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<BehavioralMetric user={self.user_id} "
            f"period={self.period_type} brs={self.behavioral_risk_score}>"
        )
