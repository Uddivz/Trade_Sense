"""
TradeSense — Holding Pydantic Schemas
"""
from datetime import datetime
from decimal import Decimal
import uuid
from pydantic import BaseModel, ConfigDict


class HoldingBase(BaseModel):
    symbol: str
    isin: str | None = None
    exchange: str = "NSE"
    sector: str | None = None
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    realized_pnl: Decimal


class HoldingResponse(HoldingBase):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "portfolio_id": "123e4567-e89b-12d3-a456-426614174000",
                "symbol": "TCS",
                "isin": "INE467B01029",
                "exchange": "NSE",
                "sector": "Technology",
                "quantity": 10.5,
                "average_cost": 3500.0,
                "market_price": 3600.0,
                "market_value": 37800.0,
                "unrealized_pnl": 1050.0,
                "unrealized_pnl_pct": 0.0285,
                "realized_pnl": 0.0,
                "updated_at": "2023-10-16T12:00:00Z"
            }
        }
    )
