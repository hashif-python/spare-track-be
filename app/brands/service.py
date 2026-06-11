from sqlalchemy.orm import Session
from app.brands.models import Brand
from app.brands.schemas import BrandCreateRequest, BrandUpdateRequest
from app.common.utils import slugify


def get_brand_by_id(db: Session, brand_id: int) -> Brand | None:
    return db.query(Brand).filter(Brand.id == brand_id).first()


def get_brand_by_name(db: Session, name: str) -> Brand | None:
    return db.query(Brand).filter(Brand.name.ilike(name.strip())).first()


def get_brand_by_slug(db: Session, slug: str) -> Brand | None:
    return db.query(Brand).filter(Brand.slug == slug).first()


def get_brands(db: Session, skip: int = 0, limit: int = 100, search: str | None = None, is_active: bool | None = None):
    query = db.query(Brand)
    if search:
        query = query.filter(Brand.name.ilike(f"%{search.strip()}%"))
    if is_active is not None:
        query = query.filter(Brand.is_active == is_active)
    return query.count(), query.order_by(Brand.created_at.desc()).offset(skip).limit(limit).all()


def create_brand(db: Session, request: BrandCreateRequest) -> Brand:
    base_slug = slugify(request.name)
    slug = base_slug
    counter = 1
    while get_brand_by_slug(db, slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    brand = Brand(name=request.name.strip(), slug=slug, description=request.description, is_active=request.is_active)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def update_brand(db: Session, brand: Brand, request: BrandUpdateRequest) -> Brand:
    if request.name is not None:
        new_name = request.name.strip()
        if new_name.lower() != brand.name.lower():
            base_slug = slugify(new_name)
            slug = base_slug
            counter = 1
            while True:
                existing = get_brand_by_slug(db, slug)
                if not existing or existing.id == brand.id:
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            brand.name = new_name
            brand.slug = slug
    if request.description is not None:
        brand.description = request.description
    if request.is_active is not None:
        brand.is_active = request.is_active
    db.commit()
    db.refresh(brand)
    return brand


def delete_brand(db: Session, brand: Brand) -> None:
    db.delete(brand)
    db.commit()
