from pydantic import BaseModel


class BrandWiseSummaryResponse(BaseModel):
    brand_id: int
    brand: str
    total_parts: int
    total_files: int
    completed_files: int
    processing_files: int
    failed_files: int
    price_changed_count: int
    found_count: int
    not_found_count: int


class DashboardSummaryResponse(BaseModel):
    total_brands: int
    total_files_uploaded: int
    total_parts: int
    completed_files: int
    processing_files: int
    failed_files: int
    total_price_changes: int
    found_count: int
    not_found_count: int
    brand_wise_summary: list[BrandWiseSummaryResponse]
