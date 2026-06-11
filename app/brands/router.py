from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.brands.schemas import (
    BrandCreateRequest,
    BrandListResponse,
    BrandResponse,
    BrandUpdateRequest,
)
from app.brands.service import (
    create_brand,
    delete_brand,
    get_brand_by_id,
    get_brand_by_name,
    get_brands,
    update_brand,
)
from app.common.dependencies import get_current_user
from app.common.exceptions import BadRequestException, NotFoundException
from app.common.responses import success_response
from app.database import get_db


router = APIRouter(
    prefix="/api/brands",
    tags=["Brands"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_brand_api(
    request: BrandCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if get_brand_by_name(db, request.name):
        raise BadRequestException("Brand name already exists")

    brand = create_brand(db, request)

    return success_response(
        message="Brand created successfully",
        data=BrandResponse.model_validate(brand).model_dump(mode="json"),
    )


@router.get("/")
def list_brands_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
):
    total, brands = get_brands(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
    )

    response_data = BrandListResponse(
        total=total,
        items=[
            BrandResponse.model_validate(brand)
            for brand in brands
        ],
    )

    return success_response(
        message="Brands fetched successfully",
        data=response_data.model_dump(mode="json"),
    )


@router.get("/{brand_id}/")
def get_brand_detail_api(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    brand = get_brand_by_id(db, brand_id)

    if not brand:
        raise NotFoundException("Brand not found")

    return success_response(
        message="Brand fetched successfully",
        data=BrandResponse.model_validate(brand).model_dump(mode="json"),
    )


@router.put("/{brand_id}/")
def update_brand_api(
    brand_id: int,
    request: BrandUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    brand = get_brand_by_id(db, brand_id)

    if not brand:
        raise NotFoundException("Brand not found")

    if request.name is not None:
        existing_brand = get_brand_by_name(db, request.name)

        if existing_brand and existing_brand.id != brand.id:
            raise BadRequestException("Brand name already exists")

    updated_brand = update_brand(
        db=db,
        brand=brand,
        request=request,
    )

    return success_response(
        message="Brand updated successfully",
        data=BrandResponse.model_validate(updated_brand).model_dump(mode="json"),
    )


@router.delete("/{brand_id}/")
def delete_brand_api(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    brand = get_brand_by_id(db, brand_id)

    if not brand:
        raise NotFoundException("Brand not found")

    delete_brand(db, brand)

    return success_response(
        message="Brand deleted successfully",
        data={
            "id": brand_id,
        },
    )