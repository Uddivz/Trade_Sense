"""
TradeSense — Analytics & Recommendation Schemas
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Analytics ───────────────────────────────────────────────────────────────────

class DispositionEffectSchema(BaseModel):
    pgr: float | None
    plr: float | None
    de_score: float | None
    classification: str | None
    realized_gains_count: int
    realized_losses_count: int
    paper_gains_count: int
    paper_losses_count: int
    status: str


class OvertradingSchema(BaseModel):
    portfolio_turnover_ratio: float | None
    trade_frequency_per_month: float | None
    total_trades: int
    cost_drag_pct: float | None
    classification: str | None
    status: str


class ConcentrationSchema(BaseModel):
    hhi: float | None
    effective_n: float | None
    top1_holding_pct: float | None
    top3_holding_pct: float | None
    num_holdings: int
    holdings_breakdown: list[dict]
    classification: str | None
    status: str


class BehavioralSummaryResponse(BaseModel):
    status: str
    message: str | None = None
    computed_at: datetime | None = None
    behavioral_risk_score: float | None = None
    disposition_effect: DispositionEffectSchema | None = None
    overtrading: OvertradingSchema | None = None
    concentration: ConcentrationSchema | None = None
    details: dict[str, Any] | None = None


# ── Recommendations ─────────────────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    id: uuid.UUID
    rule_id: str
    category: str
    severity: str
    title: str
    body: str
    status: str
    generated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    status: str
    records_parsed: int
    records_inserted: int
    records_skipped: int
    message: str
