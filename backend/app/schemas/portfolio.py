"""
TradeSense — Portfolio Schemas
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortfolioCreate(BaseModel):
    name: str
    broker_name: str | None = None
    currency: str = "INR"
    cost_basis_method: str = "FIFO"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Retirement Fund",
                "broker_name": "Zerodha",
                "currency": "INR",
                "cost_basis_method": "FIFO"
            }
        }
    )


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    broker_name: str | None
    currency: str
    cost_basis_method: str
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Retirement Fund",
                "broker_name": "Zerodha",
                "currency": "INR",
                "cost_basis_method": "FIFO",
                "is_default": True,
                "created_at": "2023-01-01T12:00:00Z"
            }
        }
    )
