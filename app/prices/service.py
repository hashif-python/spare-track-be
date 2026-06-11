from sqlalchemy.orm import Session
from app.prices.models import PriceHistory
from app.prices.schemas import PriceHistoryCreateData


def create_price_history(db: Session, data: PriceHistoryCreateData) -> PriceHistory:
    history = PriceHistory(**data.model_dump())
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def get_price_history_by_id(db: Session, history_id: int) -> PriceHistory | None:
    return db.query(PriceHistory).filter(PriceHistory.id == history_id).first()


def get_price_history_by_part(db: Session, part_id: int, skip: int = 0, limit: int = 100):
    query = db.query(PriceHistory).filter(PriceHistory.part_id == part_id)
    return query.count(), query.order_by(PriceHistory.checked_at.desc()).offset(skip).limit(limit).all()


def get_price_history_by_uploaded_file(db: Session, uploaded_file_id: int, skip: int = 0, limit: int = 100):
    query = db.query(PriceHistory).filter(PriceHistory.uploaded_file_id == uploaded_file_id)
    return query.count(), query.order_by(PriceHistory.checked_at.desc()).offset(skip).limit(limit).all()


def get_total_price_changes(db: Session) -> int:
    return db.query(PriceHistory).filter(PriceHistory.price_changed.is_(True)).count()
