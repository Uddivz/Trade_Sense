"""
TradeSense — Transaction Pydantic Schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar
import uuid
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated envelope used by list endpoints."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionBase(BaseModel):
    symbol: str = Field(..., max_length=50)
    isin: str | None = Field(None, max_length=12)
    exchange: str = Field("NSE", max_length=20)
    transaction_type: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    total_value: Decimal = Field(...)
    brokerage: Decimal = Field(default=Decimal("0.0"))
    stt: Decimal = Field(default=Decimal("0.0"))
    other_charges: Decimal = Field(default=Decimal("0.0"))
    net_value: Decimal = Field(...)
    trade_date: date
    notes: str | None = None
    broker_trade_id: str | None = Field(None, max_length=100)
    external_trade_id: str | None = Field(None, max_length=100)
    broker: str | None = Field(None, max_length=100)
    fees: Decimal = Field(default=Decimal("0.0"))
    raw_data: dict[str, Any] | None = None


class TransactionCreate(TransactionBase):
    portfolio_id: uuid.UUID


class TransactionResponse(TransactionBase):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "portfolio_id": "123e4567-e89b-12d3-a456-426614174000",
                "symbol": "TCS",
                "isin": "INE467B01029",
                "exchange": "NSE",
                "transaction_type": "BUY",
                "quantity": 10.5,
                "price": 3500.0,
                "total_value": 36750.0,
                "brokerage": 20.0,
                "stt": 36.75,
                "other_charges": 5.0,
                "net_value": 36811.75,
                "trade_date": "2023-10-15",
                "notes": "Long term holding",
                "broker_trade_id": "87654321",
                "external_trade_id": "EXT123",
                "broker": "Zerodha",
                "fees": 61.75,
                "created_at": "2023-10-16T12:00:00Z",
                "updated_at": None,
                "raw_data": {}
            }
        }
    )
