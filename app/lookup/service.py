from decimal import Decimal
from typing import Any

from app.config import settings
from app.lookup.base import BaseLookupProvider
from app.lookup.web_claude_provider import WebClaudeLookupProvider


class PartLookupService:
    def __init__(self) -> None:
        self.provider = self._get_provider()

    def lookup_new_part(
        self,
        brand_name: str,
        part_number: str,
    ) -> dict[str, Any]:
        result = self.provider.lookup_new_part(
            brand_name=brand_name,
            part_number=part_number,
        )

        return self._normalize_new_part_result(
            brand_name=brand_name,
            part_number=part_number,
            result=result,
        )

    def lookup_market_price(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> dict[str, Any]:
        result = self.provider.lookup_market_price(
            brand_name=brand_name,
            part_number=part_number,
            product_name=product_name,
        )

        return self._normalize_market_price_result(result)

    def lookup_new_parts_batch(
        self,
        brand_name: str,
        part_numbers: list[str],
    ) -> dict[str, dict[str, Any]]:
        raw_results = self.provider.lookup_new_parts_batch(
            brand_name=brand_name,
            part_numbers=part_numbers,
        )

        normalized_results = {}

        for part_number in part_numbers:
            normalized_part_number = str(part_number).strip().upper()
            result = raw_results.get(normalized_part_number, {})

            normalized_results[normalized_part_number] = self._normalize_new_part_result(
                brand_name=brand_name,
                part_number=normalized_part_number,
                result=result,
            )

        return normalized_results

    def lookup_market_prices_batch(
        self,
        brand_name: str,
        parts: list[dict[str, str | None]],
    ) -> dict[str, dict[str, Any]]:
        raw_results = self.provider.lookup_market_prices_batch(
            brand_name=brand_name,
            parts=parts,
        )

        normalized_results = {}

        for item in parts:
            part_number = str(item.get("part_number") or "").strip().upper()

            if not part_number:
                continue

            result = raw_results.get(part_number, {})

            normalized_results[part_number] = self._normalize_market_price_result(result)

        return normalized_results

    def _get_provider(self) -> BaseLookupProvider:
        provider_name = settings.LOOKUP_PROVIDER.lower().strip()

        if provider_name == "web_claude":
            return WebClaudeLookupProvider()

        raise ValueError(
            f"Invalid LOOKUP_PROVIDER={settings.LOOKUP_PROVIDER}. "
            "Allowed value is: web_claude"
        )

    def _normalize_new_part_result(
        self,
        brand_name: str,
        part_number: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        market_price = self._to_decimal_or_none(result.get("market_price"))

        return {
            "part_number": str(result.get("part_number") or part_number).strip().upper(),
            "brand": result.get("brand") or brand_name,
            "product_name": result.get("product_name") or "Not Found",
            "description": result.get("description") or "Not Found",
            "market_price": market_price,
            "currency": result.get("currency") or settings.DEFAULT_CURRENCY,
            "source_url": result.get("source_url"),
            "lookup_status": result.get("lookup_status") or "not_found",
            "confidence": result.get("confidence", 0),
        }

    def _normalize_market_price_result(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        market_price = self._to_decimal_or_none(result.get("market_price"))
        lookup_status = result.get("lookup_status")

        if market_price is None and lookup_status == "price_found":
            lookup_status = "price_not_available"

        return {
            "part_number": str(result.get("part_number") or "").strip().upper(),
            "market_price": market_price,
            "currency": result.get("currency") or settings.DEFAULT_CURRENCY,
            "source_url": result.get("source_url"),
            "lookup_status": lookup_status or "price_not_available",
            "confidence": result.get("confidence", 0),
        }

    def _to_decimal_or_none(self, value: Any) -> Decimal | None:
        if value is None:
            return None

        try:
            return Decimal(str(value))
        except Exception:
            return None