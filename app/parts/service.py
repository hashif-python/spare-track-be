from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.utils import normalize_part_number
from app.parts.models import Part
from app.parts.schemas import PartCreateRequest, PartUpdateRequest


def get_part_by_id(db: Session, part_id: int) -> Part | None:
    return db.query(Part).filter(Part.id == part_id).first()


def get_part_by_brand_and_number(
    db: Session,
    brand_id: int,
    part_number: str,
) -> Part | None:
    normalized_part_number = normalize_part_number(part_number)

    return (
        db.query(Part)
        .filter(
            Part.brand_id == brand_id,
            Part.part_number == normalized_part_number,
        )
        .first()
    )


def get_parts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    brand_id: int | None = None,
    search: str | None = None,
    lookup_status: str | None = None,
) -> tuple[int, list[Part]]:
    query = db.query(Part)

    if brand_id is not None:
        query = query.filter(Part.brand_id == brand_id)

    if search:
        search_value = f"%{search.strip()}%"
        query = query.filter(
            Part.part_number.ilike(search_value)
            | Part.product_name.ilike(search_value)
            | Part.description.ilike(search_value)
        )

    if lookup_status:
        query = query.filter(Part.lookup_status == lookup_status)

    total = query.count()

    parts = (
        query
        .order_by(Part.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return total, parts


def create_part(
    db: Session,
    request: PartCreateRequest,
) -> Part:
    part = Part(
        brand_id=request.brand_id,
        part_number=normalize_part_number(request.part_number),
        product_name=request.product_name,
        description=request.description,
        current_price=request.current_price,
        previous_price=request.previous_price,
        currency=request.currency,
        source_url=request.source_url,
        lookup_status=request.lookup_status,
        last_checked_at=datetime.now(timezone.utc),
    )

    db.add(part)
    db.commit()
    db.refresh(part)

    return part


def create_part_from_lookup(
    db: Session,
    brand_id: int,
    part_number: str,
    lookup_data: dict,
) -> Part:
    market_price = lookup_data.get("market_price")

    part = Part(
        brand_id=brand_id,
        part_number=normalize_part_number(part_number),
        product_name=lookup_data.get("product_name"),
        description=lookup_data.get("description"),
        current_price=Decimal(str(market_price)) if market_price is not None else None,
        previous_price=None,
        currency=lookup_data.get("currency") or "USD",
        source_url=lookup_data.get("source_url"),
        lookup_status=lookup_data.get("lookup_status") or "not_found",
        last_checked_at=datetime.now(timezone.utc),
    )

    db.add(part)
    db.commit()
    db.refresh(part)

    return part


def update_part(
    db: Session,
    part: Part,
    request: PartUpdateRequest,
) -> Part:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(part, field, value)

    part.last_checked_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(part)

    return part


def update_part_price(
    db: Session,
    part: Part,
    new_price: Decimal | None,
    currency: str | None,
    source_url: str | None,
    lookup_status: str,
) -> tuple[Part, bool]:
    """
    Price update rule:

    If new_price is None:
    - Do not overwrite current_price
    - Set lookup_status = price_not_available
    - Clear old mock source URL if real lookup failed

    If price changed:
    - previous_price = old current_price
    - current_price = new_price
    """

    price_changed = False

    if new_price is None:
        part.lookup_status = "price_not_available"
        part.last_checked_at = datetime.now(timezone.utc)

        if currency:
            part.currency = currency

        # Important fix:
        # If the old source came from mock provider and real lookup failed,
        # do not keep fake mock URL in Excel output.
        if part.source_url and "mock.sparetrack.local" in part.source_url:
            part.source_url = None

        if source_url:
            part.source_url = source_url

        db.commit()
        db.refresh(part)

        return part, price_changed

    new_price_decimal = Decimal(str(new_price))
    old_price = part.current_price

    if old_price is not None and Decimal(str(old_price)) != new_price_decimal:
        part.previous_price = old_price
        part.current_price = new_price_decimal
        price_changed = True

    elif old_price is None:
        part.current_price = new_price_decimal
        price_changed = False

    else:
        price_changed = False

    if currency:
        part.currency = currency

    if source_url:
        part.source_url = source_url

    part.lookup_status = lookup_status
    part.last_checked_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(part)

    return part, price_changed


def delete_part(
    db: Session,
    part: Part,
) -> None:
    db.delete(part)
    db.commit()