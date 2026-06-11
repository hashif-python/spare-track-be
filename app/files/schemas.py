from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class UploadedFileStatusSchema(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadedFileResponse(BaseModel):
    id: int
    user_id: int
    brand_id: int
    original_filename: str
    original_file_path: str
    processed_file_path: str | None
    status: UploadedFileStatusSchema
    total_rows: int
    processed_rows: int
    found_count: int
    not_found_count: int
    price_changed_count: int
    error_message: str | None
    uploaded_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadedFileListResponse(BaseModel):
    total: int
    items: list[UploadedFileResponse]


class UploadedFileCreateData(BaseModel):
    user_id: int
    brand_id: int
    original_filename: str
    original_file_path: str


class UploadedFileProgressUpdate(BaseModel):
    total_rows: int | None = None
    processed_rows: int | None = None
    found_count: int | None = None
    not_found_count: int | None = None
    price_changed_count: int | None = None


class FileUploadResponse(BaseModel):
    file: UploadedFileResponse
    detected_part_number_column: str
    celery_task_id: str | None = None
    next_step: str
