"""
TradeSense — Portfolio Schemas
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class PortfolioCreate(BaseModel):
    name: str
    broker_name: str | None = None
    currency: str = "INR"
    cost_basis_method: str = "FIFO"


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    broker_name: str | None
    currency: str
    cost_basis_method: str
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}
