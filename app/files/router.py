from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.auth.models import User
from app.brands.service import get_brand_by_id
from app.common.dependencies import get_current_user
from app.common.exceptions import BadRequestException, NotFoundException
from app.common.responses import success_response
from app.database import get_db
from app.files.models import UploadedFileStatus
from app.files.schemas import FileUploadResponse, UploadedFileCreateData, UploadedFileListResponse, UploadedFileResponse
from app.files.service import create_uploaded_file, delete_uploaded_file, generate_unique_filename, get_file_status_value, get_original_file_path, get_uploaded_file_by_id, get_uploaded_files, is_valid_upload_extension, save_upload_file
from app.logs.schemas import ProcessingLogListResponse, ProcessingLogResponse
from app.logs.service import get_logs_by_uploaded_file
from app.processing.tasks import process_uploaded_file
from app.processing.utils import validate_part_number_column


router = APIRouter(prefix="/api/files", tags=["Files"])


def check_file_owner_or_admin(uploaded_file, current_user: User) -> None:
    if current_user.is_admin:
        return
    if uploaded_file.user_id != current_user.id:
        raise NotFoundException("Uploaded file not found")


@router.post("/upload/", status_code=status.HTTP_201_CREATED)
async def upload_file_api(brand_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    brand = get_brand_by_id(db, brand_id)
    if not brand:
        raise NotFoundException("Brand not found")
    if not brand.is_active:
        raise BadRequestException("Selected brand is inactive")
    if not file.filename:
        raise BadRequestException("File is required")
    if not is_valid_upload_extension(file.filename):
        raise BadRequestException("Only .xlsx and .csv files are allowed")

    unique_filename = generate_unique_filename(file.filename)
    saved_file_path = get_original_file_path(unique_filename)

    try:
        await save_upload_file(file, saved_file_path)
        detected_part_number_column = validate_part_number_column(saved_file_path)
    except ValueError as exc:
        Path(saved_file_path).unlink(missing_ok=True)
        raise BadRequestException(str(exc))
    except Exception as exc:
        Path(saved_file_path).unlink(missing_ok=True)
        raise BadRequestException(f"File validation failed: {str(exc)}")

    uploaded_file = create_uploaded_file(db, UploadedFileCreateData(user_id=current_user.id, brand_id=brand.id, original_filename=file.filename, original_file_path=saved_file_path))
    celery_task = process_uploaded_file.delay(uploaded_file.id)

    response_data = FileUploadResponse(file=UploadedFileResponse.model_validate(uploaded_file), detected_part_number_column=detected_part_number_column, celery_task_id=celery_task.id, next_step="File uploaded successfully. Background processing started.")
    return success_response("File uploaded successfully", response_data.model_dump(mode="json"))


@router.get("/")
def list_uploaded_files_api(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), brand_id: int | None = None, status_filter: UploadedFileStatus | None = None):
    total, uploaded_files = get_uploaded_files(db, skip, limit, brand_id, None if current_user.is_admin else current_user.id, status_filter)
    data = UploadedFileListResponse(total=total, items=[UploadedFileResponse.model_validate(f) for f in uploaded_files])
    return success_response("Uploaded files fetched successfully", data.model_dump(mode="json"))


@router.get("/{file_id}/")
def get_uploaded_file_detail_api(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uploaded_file = get_uploaded_file_by_id(db, file_id)
    if not uploaded_file:
        raise NotFoundException("Uploaded file not found")
    check_file_owner_or_admin(uploaded_file, current_user)
    return success_response("Uploaded file fetched successfully", UploadedFileResponse.model_validate(uploaded_file).model_dump(mode="json"))


@router.get("/{file_id}/download/")
def download_processed_file_api(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uploaded_file = get_uploaded_file_by_id(db, file_id)
    if not uploaded_file:
        raise NotFoundException("Uploaded file not found")
    check_file_owner_or_admin(uploaded_file, current_user)

    file_status = get_file_status_value(uploaded_file)
    if file_status != UploadedFileStatus.COMPLETED.value:
        raise BadRequestException(f"Processed file is not ready. Current status: {file_status}")
    if not uploaded_file.processed_file_path:
        raise NotFoundException("Processed file path not found")

    processed_path = Path(uploaded_file.processed_file_path)
    if not processed_path.exists():
        raise NotFoundException("Processed file not found on server")

    download_filename = f"processed_{uploaded_file.original_filename}"
    if not download_filename.lower().endswith(".xlsx"):
        download_filename = f"{Path(download_filename).stem}.xlsx"

    return FileResponse(str(processed_path), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=download_filename)


@router.get("/{file_id}/logs/")
def get_uploaded_file_logs_api(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), skip: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000)):
    uploaded_file = get_uploaded_file_by_id(db, file_id)
    if not uploaded_file:
        raise NotFoundException("Uploaded file not found")
    check_file_owner_or_admin(uploaded_file, current_user)
    total, logs = get_logs_by_uploaded_file(db, file_id, skip, limit)
    data = ProcessingLogListResponse(total=total, items=[ProcessingLogResponse.model_validate(log) for log in logs])
    return success_response("Processing logs fetched successfully", data.model_dump(mode="json"))


@router.delete("/{file_id}/")
def delete_uploaded_file_api(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uploaded_file = get_uploaded_file_by_id(db, file_id)
    if not uploaded_file:
        raise NotFoundException("Uploaded file not found")
    check_file_owner_or_admin(uploaded_file, current_user)
    if get_file_status_value(uploaded_file) == UploadedFileStatus.PROCESSING.value:
        raise BadRequestException("Cannot delete file while processing is running")
    delete_uploaded_file(db, uploaded_file, True)
    return success_response("Uploaded file deleted successfully", {"id": file_id})
