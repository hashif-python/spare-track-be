from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class PartBase(BaseModel):
    product_name: str | None = None
    description: str | None = None
    current_price: Decimal | None = None
    previous_price: Decimal | None = None
    currency: str = "USD"
    source_url: str | None = None
    lookup_status: str = "pending"


class PartCreateRequest(PartBase):
    brand_id: int
    part_number: str = Field(..., min_length=1, max_length=150)


class PartUpdateRequest(BaseModel):
    product_name: str | None = None
    description: str | None = None
    current_price: Decimal | None = None
    previous_price: Decimal | None = None
    currency: str | None = None
    source_url: str | None = None
    lookup_status: str | None = None


class PartResponse(BaseModel):
    id: int
    brand_id: int
    part_number: str
    product_name: str | None
    description: str | None
    current_price: Decimal | None
    previous_price: Decimal | None
    currency: str
    source_url: str | None
    last_checked_at: datetime | None
    lookup_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartListResponse(BaseModel):
    total: int
    items: list[PartResponse]


class PartSearchResponse(BaseModel):
    exists: bool
    part: PartResponse | None = None


class ManualPriceRecheckResponse(BaseModel):
    part: PartResponse
    old_price: Decimal | None
    new_price: Decimal | None
    price_changed: bool
    lookup_status: str
    source_url: str | None
