from fastapi import APIRouter, Depends, Query

from app.auth.models import User
from app.common.dependencies import get_current_user
from app.common.responses import success_response
from app.lookup.service import PartLookupService


router = APIRouter(
    prefix="/api/lookup",
    tags=["Lookup"],
)


@router.get("/check-internet/")
def check_internet_lookup_api(
    brand_name: str = Query(..., example="Dell"),
    part_number: str = Query(..., example="KGTXJ"),
    product_name: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    lookup_service = PartLookupService()

    if product_name:
        result = lookup_service.lookup_market_price(
            brand_name=brand_name,
            part_number=part_number,
            product_name=product_name,
        )

        return success_response(
            message="Internet price lookup completed",
            data=result,
        )

    result = lookup_service.lookup_new_part(
        brand_name=brand_name,
        part_number=part_number,
    )

    return success_response(
        message="Internet part lookup completed",
        data=result,
    )


@router.get("/new-part/")
def lookup_new_part_api(
    brand_name: str = Query(..., example="Dell"),
    part_number: str = Query(..., example="KGTXJ"),
    current_user: User = Depends(get_current_user),
):
    result = PartLookupService().lookup_new_part(
        brand_name=brand_name,
        part_number=part_number,
    )

    return success_response(
        message="New part lookup completed",
        data=result,
    )


@router.get("/market-price/")
def lookup_market_price_api(
    brand_name: str = Query(..., example="Dell"),
    part_number: str = Query(..., example="KGTXJ"),
    product_name: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    result = PartLookupService().lookup_market_price(
        brand_name=brand_name,
        part_number=part_number,
        product_name=product_name,
    )

    return success_response(
        message="Market price lookup completed",
        data=result,
    )