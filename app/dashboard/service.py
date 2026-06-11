from sqlalchemy import func
from sqlalchemy.orm import Session
from app.brands.models import Brand
from app.files.models import UploadedFile, UploadedFileStatus
from app.parts.models import Part
from app.prices.models import PriceHistory


def get_dashboard_summary(db: Session) -> dict:
    found_count = db.query(func.coalesce(func.sum(UploadedFile.found_count), 0)).scalar()
    not_found_count = db.query(func.coalesce(func.sum(UploadedFile.not_found_count), 0)).scalar()

    return {
        "total_brands": db.query(Brand).count(),
        "total_files_uploaded": db.query(UploadedFile).count(),
        "total_parts": db.query(Part).count(),
        "completed_files": db.query(UploadedFile).filter(UploadedFile.status == UploadedFileStatus.COMPLETED).count(),
        "processing_files": db.query(UploadedFile).filter(UploadedFile.status == UploadedFileStatus.PROCESSING).count(),
        "failed_files": db.query(UploadedFile).filter(UploadedFile.status == UploadedFileStatus.FAILED).count(),
        "total_price_changes": db.query(PriceHistory).filter(PriceHistory.price_changed.is_(True)).count(),
        "found_count": int(found_count or 0),
        "not_found_count": int(not_found_count or 0),
        "brand_wise_summary": get_brand_wise_summary(db),
    }


def get_brand_wise_summary(db: Session) -> list[dict]:
    summary = []
    for brand in db.query(Brand).order_by(Brand.name.asc()).all():
        found_count = db.query(func.coalesce(func.sum(UploadedFile.found_count), 0)).filter(UploadedFile.brand_id == brand.id).scalar()
        not_found_count = db.query(func.coalesce(func.sum(UploadedFile.not_found_count), 0)).filter(UploadedFile.brand_id == brand.id).scalar()
        summary.append({
            "brand_id": brand.id,
            "brand": brand.name,
            "total_parts": db.query(Part).filter(Part.brand_id == brand.id).count(),
            "total_files": db.query(UploadedFile).filter(UploadedFile.brand_id == brand.id).count(),
            "completed_files": db.query(UploadedFile).filter(UploadedFile.brand_id == brand.id, UploadedFile.status == UploadedFileStatus.COMPLETED).count(),
            "processing_files": db.query(UploadedFile).filter(UploadedFile.brand_id == brand.id, UploadedFile.status == UploadedFileStatus.PROCESSING).count(),
            "failed_files": db.query(UploadedFile).filter(UploadedFile.brand_id == brand.id, UploadedFile.status == UploadedFileStatus.FAILED).count(),
            "price_changed_count": db.query(PriceHistory).join(Part, PriceHistory.part_id == Part.id).filter(Part.brand_id == brand.id, PriceHistory.price_changed.is_(True)).count(),
            "found_count": int(found_count or 0),
            "not_found_count": int(not_found_count or 0),
        })
    return summary
