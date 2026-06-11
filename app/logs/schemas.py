from datetime import datetime
from pydantic import BaseModel


class ProcessingLogCreateData(BaseModel):
    uploaded_file_id: int
    brand_id: int
    part_number: str | None = None
    row_number: int | None = None
    status: str
    message: str | None = None


class ProcessingLogResponse(BaseModel):
    id: int
    uploaded_file_id: int
    brand_id: int
    part_number: str | None
    row_number: int | None
    status: str
    message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProcessingLogListResponse(BaseModel):
    total: int
    items: list[ProcessingLogResponse]
