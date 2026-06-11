from pydantic import BaseModel, Field, field_validator


class WebSearchResult(BaseModel):
    title: str | None = None
    url: str | None = None
    content: str | None = None


class NewPartLookupOutput(BaseModel):
    part_number: str
    brand: str
    product_name: str
    description: str
    market_price: float | None = None
    currency: str = "USD"
    source_url: str | None = None
    lookup_status: str = "not_found"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("lookup_status")
    @classmethod
    def validate_lookup_status(cls, value: str) -> str:
        value = value.strip().lower()
        return value if value in {"found", "not_found"} else "not_found"

    @field_validator("market_price")
    @classmethod
    def validate_market_price(cls, value: float | None) -> float | None:
        if value is None or value < 0:
            return None

        return round(float(value), 2)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return (value or "USD").strip().upper()[:10]

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if not value:
            return None

        value = value.strip()

        if not value.startswith(("http://", "https://")):
            return None

        return value


class MarketPriceLookupOutput(BaseModel):
    part_number: str
    market_price: float | None = None
    currency: str = "USD"
    source_url: str | None = None
    lookup_status: str = "price_not_available"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("lookup_status")
    @classmethod
    def validate_lookup_status(cls, value: str) -> str:
        value = value.strip().lower()
        return value if value in {"price_found", "price_not_available"} else "price_not_available"

    @field_validator("market_price")
    @classmethod
    def validate_market_price(cls, value: float | None) -> float | None:
        if value is None or value < 0:
            return None

        return round(float(value), 2)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return (value or "USD").strip().upper()[:10]

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if not value:
            return None

        value = value.strip()

        if not value.startswith(("http://", "https://")):
            return None

        return value


class NewPartBatchLookupOutput(BaseModel):
    results: list[NewPartLookupOutput]


class MarketPriceBatchLookupOutput(BaseModel):
    results: list[MarketPriceLookupOutput]