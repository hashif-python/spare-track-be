from app.celery_app import celery
from app.database import SessionLocal
from app.files.models import UploadedFileStatus
from app.files.service import get_uploaded_file_by_id, update_file_status
from app.logs.schemas import ProcessingLogCreateData
from app.logs.service import create_processing_log
from app.processing.excel_processor import ExcelProcessor
import app.models

@celery.task(name="app.processing.tasks.process_uploaded_file", bind=True, max_retries=3)
def process_uploaded_file(self, file_id: int) -> dict:
    db = SessionLocal()
    try:
        uploaded_file = get_uploaded_file_by_id(db, file_id)
        if not uploaded_file:
            return {"success": False, "message": f"Uploaded file with id {file_id} not found", "file_id": file_id}

        processed_file = ExcelProcessor(db).process_uploaded_file(uploaded_file)
        status_value = processed_file.status.value if hasattr(processed_file.status, "value") else str(processed_file.status)

        return {
            "success": True,
            "message": "File processed successfully",
            "file_id": processed_file.id,
            "status": status_value,
            "processed_file_path": processed_file.processed_file_path,
            "total_rows": processed_file.total_rows,
            "processed_rows": processed_file.processed_rows,
            "found_count": processed_file.found_count,
            "not_found_count": processed_file.not_found_count,
            "price_changed_count": processed_file.price_changed_count,
        }

    except Exception as exc:
        db.rollback()
        uploaded_file = get_uploaded_file_by_id(db, file_id)
        if uploaded_file:
            update_file_status(db, uploaded_file, UploadedFileStatus.FAILED, str(exc))
            create_processing_log(db, ProcessingLogCreateData(uploaded_file_id=uploaded_file.id, brand_id=uploaded_file.brand_id, status="failed", message=f"Celery task failed: {str(exc)}"))
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
