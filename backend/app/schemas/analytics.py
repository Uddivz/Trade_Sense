"""
TradeSense — Analytics Pydantic Schemas
"""
from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class UploadResponse(BaseModel):
    status: str
    records_parsed: int
    records_inserted: int
    records_skipped: int = 0
    message: str | None = None


class BehavioralMetricResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    period_type: str
    pgr: float | None = None
    plr: float | None = None
    disposition_effect_score: float | None = None
    portfolio_turnover_ratio: float | None = None
    hhi: float | None = None
    cost_drag_pct: float | None = None
    metric_details: dict | None = None
    computed_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "portfolio_id": "123e4567-e89b-12d3-a456-426614174000",
                "period_type": "ALL_TIME",
                "pgr": 0.65,
                "plr": 0.20,
                "disposition_effect_score": 0.45,
                "portfolio_turnover_ratio": 0.15,
                "hhi": 3050.5,
                "cost_drag_pct": 0.02,
                "metric_details": {
                    "realized_gains": 5000.0,
                    "paper_gains": 2500.0
                },
                "computed_at": "2023-10-15T12:00:00Z"
            }
        }
    )


class RecommendationResponse(BaseModel):
    id: uuid.UUID
    rule_id: str
    category: str
    severity: str
    title: str
    body: str
    status: str
    supporting_data: dict | None = None
    generated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "rule_id": "R001",
                "category": "Behavioral Bias",
                "severity": "HIGH",
                "title": "High Disposition Effect Detected",
                "body": "You are systematically selling your winning positions too early.",
                "status": "ACTIVE",
                "supporting_data": {"de_score": 0.45},
                "generated_at": "2023-10-15T12:00:00Z"
            }
        }
    )
