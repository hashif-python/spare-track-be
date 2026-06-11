from datetime import datetime
from pydantic import BaseModel, Field


class BrandCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    is_active: bool = True


class BrandUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class BrandResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BrandListResponse(BaseModel):
    total: int
    items: list[BrandResponse]
