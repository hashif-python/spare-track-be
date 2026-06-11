from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class PriceHistoryCreateData(BaseModel):
    part_id: int
    uploaded_file_id: int | None = None
    old_price: Decimal | None = None
    new_price: Decimal | None = None
    currency: str = "USD"
    source_url: str | None = None
    price_changed: bool = False


class PriceHistoryResponse(BaseModel):
    id: int
    part_id: int
    uploaded_file_id: int | None
    old_price: Decimal | None
    new_price: Decimal | None
    currency: str
    source_url: str | None
    price_changed: bool
    checked_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class PriceHistoryListResponse(BaseModel):
    total: int
    items: list[PriceHistoryResponse]
