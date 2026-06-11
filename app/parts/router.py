from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.models import User
from app.brands.service import get_brand_by_id
from app.common.dependencies import get_current_user
from app.common.exceptions import BadRequestException, NotFoundException
from app.common.responses import success_response
from app.database import get_db
from app.lookup.service import PartLookupService
from app.parts.schemas import ManualPriceRecheckResponse, PartListResponse, PartResponse, PartSearchResponse, PartUpdateRequest
from app.parts.service import get_part_by_brand_and_number, get_part_by_id, get_parts, update_part, update_part_price
from app.prices.schemas import PriceHistoryCreateData, PriceHistoryListResponse, PriceHistoryResponse
from app.prices.service import create_price_history, get_price_history_by_part


router = APIRouter(prefix="/api/parts", tags=["Parts"])


@router.get("/")
def list_parts_api(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), brand_id: int | None = None, search: str | None = None, lookup_status: str | None = None):
    total, parts = get_parts(db, skip, limit, brand_id, search, lookup_status)
    data = PartListResponse(total=total, items=[PartResponse.model_validate(p) for p in parts])
    return success_response("Parts fetched successfully", data.model_dump(mode="json"))


@router.get("/by-brand/{brand_id}/")
def list_parts_by_brand_api(brand_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), search: str | None = None, lookup_status: str | None = None):
    if not get_brand_by_id(db, brand_id):
        raise NotFoundException("Brand not found")
    total, parts = get_parts(db, skip, limit, brand_id, search, lookup_status)
    data = PartListResponse(total=total, items=[PartResponse.model_validate(p) for p in parts])
    return success_response("Brand parts fetched successfully", data.model_dump(mode="json"))


@router.get("/search/")
def search_part_api(brand_id: int = Query(...), part_number: str = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not get_brand_by_id(db, brand_id):
        raise NotFoundException("Brand not found")
    part = get_part_by_brand_and_number(db, brand_id, part_number)
    data = PartSearchResponse(exists=part is not None, part=PartResponse.model_validate(part) if part else None)
    return success_response("Part search completed", data.model_dump(mode="json"))


@router.get("/{part_id}/")
def get_part_detail_api(part_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    part = get_part_by_id(db, part_id)
    if not part:
        raise NotFoundException("Part not found")
    return success_response("Part fetched successfully", PartResponse.model_validate(part).model_dump(mode="json"))


@router.put("/{part_id}/")
def update_part_api(part_id: int, request: PartUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    part = get_part_by_id(db, part_id)
    if not part:
        raise NotFoundException("Part not found")
    updated = update_part(db, part, request)
    return success_response("Part updated successfully", PartResponse.model_validate(updated).model_dump(mode="json"))


@router.get("/{part_id}/price-history/")
def get_part_price_history_api(part_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    if not get_part_by_id(db, part_id):
        raise NotFoundException("Part not found")
    total, history = get_price_history_by_part(db, part_id, skip, limit)
    data = PriceHistoryListResponse(total=total, items=[PriceHistoryResponse.model_validate(h) for h in history])
    return success_response("Price history fetched successfully", data.model_dump(mode="json"))


@router.post("/{part_id}/recheck-price/")
def recheck_part_price_api(part_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    part = get_part_by_id(db, part_id)
    if not part:
        raise NotFoundException("Part not found")
    if not part.brand:
        raise BadRequestException("Part brand not found")

    old_price = part.current_price
    lookup = PartLookupService().lookup_market_price(part.brand.name, part.part_number, part.product_name)
    new_price = lookup.get("market_price")
    currency = lookup.get("currency")
    source_url = lookup.get("source_url")
    lookup_status = lookup.get("lookup_status") or "price_not_available"

    updated, price_changed = update_part_price(db, part, new_price, currency, source_url, lookup_status)
    create_price_history(db, PriceHistoryCreateData(part_id=updated.id, uploaded_file_id=None, old_price=old_price, new_price=new_price, currency=currency or updated.currency, source_url=source_url, price_changed=price_changed))

    data = ManualPriceRecheckResponse(part=PartResponse.model_validate(updated), old_price=old_price, new_price=new_price, price_changed=price_changed, lookup_status=updated.lookup_status, source_url=updated.source_url)
    return success_response("Part price rechecked successfully", data.model_dump(mode="json"))
