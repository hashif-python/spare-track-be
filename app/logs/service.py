from sqlalchemy.orm import Session
from app.logs.models import ProcessingLog
from app.logs.schemas import ProcessingLogCreateData


def create_processing_log(db: Session, data: ProcessingLogCreateData) -> ProcessingLog:
    log = ProcessingLog(**data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_logs_by_uploaded_file(db: Session, uploaded_file_id: int, skip: int = 0, limit: int = 500):
    query = db.query(ProcessingLog).filter(ProcessingLog.uploaded_file_id == uploaded_file_id)
    return query.count(), query.order_by(ProcessingLog.created_at.asc()).offset(skip).limit(limit).all()


def get_logs_by_brand(db: Session, brand_id: int, skip: int = 0, limit: int = 500):
    query = db.query(ProcessingLog).filter(ProcessingLog.brand_id == brand_id)
    return query.count(), query.order_by(ProcessingLog.created_at.desc()).offset(skip).limit(limit).all()
