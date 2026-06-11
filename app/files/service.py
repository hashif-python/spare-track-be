from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.config import settings
from app.files.models import UploadedFile, UploadedFileStatus
from app.files.schemas import UploadedFileCreateData, UploadedFileProgressUpdate


def generate_unique_filename(original_filename: str) -> str:
    extension = Path(original_filename).suffix.lower()
    return f"{uuid4().hex}{extension}"


def get_original_file_path(filename: str) -> str:
    return str(Path(settings.ORIGINAL_FILE_DIR) / filename)


def get_processed_file_path(filename: str) -> str:
    return str(Path(settings.PROCESSED_FILE_DIR) / filename)


def is_valid_upload_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in [".xlsx", ".csv"]


def get_file_status_value(uploaded_file: UploadedFile) -> str:
    return uploaded_file.status.value if hasattr(uploaded_file.status, "value") else str(uploaded_file.status)


async def save_upload_file(upload_file: UploadFile, destination_path: str) -> int:
    file_size = 0
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > settings.max_upload_size_bytes:
                destination.unlink(missing_ok=True)
                raise ValueError(f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB")
            buffer.write(chunk)
    await upload_file.seek(0)
    return file_size


def create_uploaded_file(db: Session, data: UploadedFileCreateData) -> UploadedFile:
    uploaded_file = UploadedFile(
        user_id=data.user_id,
        brand_id=data.brand_id,
        original_filename=data.original_filename,
        original_file_path=data.original_file_path,
        status=UploadedFileStatus.PENDING,
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)
    return uploaded_file


def get_uploaded_file_by_id(db: Session, file_id: int) -> UploadedFile | None:
    return db.query(UploadedFile).filter(UploadedFile.id == file_id).first()


def get_uploaded_files(db: Session, skip: int = 0, limit: int = 100, brand_id: int | None = None, user_id: int | None = None, status: UploadedFileStatus | None = None):
    query = db.query(UploadedFile)
    if brand_id is not None:
        query = query.filter(UploadedFile.brand_id == brand_id)
    if user_id is not None:
        query = query.filter(UploadedFile.user_id == user_id)
    if status is not None:
        query = query.filter(UploadedFile.status == status)
    return query.count(), query.order_by(UploadedFile.created_at.desc()).offset(skip).limit(limit).all()


def update_file_status(db: Session, uploaded_file: UploadedFile, status: UploadedFileStatus, error_message: str | None = None) -> UploadedFile:
    uploaded_file.status = status
    if error_message:
        uploaded_file.error_message = error_message
    if status == UploadedFileStatus.COMPLETED:
        uploaded_file.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(uploaded_file)
    return uploaded_file


def update_file_progress(db: Session, uploaded_file: UploadedFile, progress: UploadedFileProgressUpdate) -> UploadedFile:
    for field in ["total_rows", "processed_rows", "found_count", "not_found_count", "price_changed_count"]:
        value = getattr(progress, field)
        if value is not None:
            setattr(uploaded_file, field, value)
    db.commit()
    db.refresh(uploaded_file)
    return uploaded_file


def set_processed_file_path(db: Session, uploaded_file: UploadedFile, processed_file_path: str) -> UploadedFile:
    uploaded_file.processed_file_path = processed_file_path
    db.commit()
    db.refresh(uploaded_file)
    return uploaded_file


def delete_uploaded_file(db: Session, uploaded_file: UploadedFile, delete_files_from_disk: bool = True) -> None:
    original_path = uploaded_file.original_file_path
    processed_path = uploaded_file.processed_file_path
    db.delete(uploaded_file)
    db.commit()
    if delete_files_from_disk:
        for path in [original_path, processed_path]:
            if path and Path(path).exists():
                Path(path).unlink()
