import re
from typing import Any

from app.config import settings
from app.lookup.base import BaseLookupProvider
from app.lookup.search import SearchClient


class WebLookupProvider(BaseLookupProvider):
    """
    Real web lookup provider without OpenAI.

    This provider:
    - searches Google Custom Search API or SerpAPI
    - reads title, snippet, URL
    - extracts price using regex
    - builds product name and description from search result text
    - returns required structured response
    """

    def __init__(self) -> None:
        self.search_client = SearchClient()

    def lookup_new_part(
        self,
        brand_name: str,
        part_number: str,
    ) -> dict[str, Any]:
        query = self._build_new_part_query(
            brand_name=brand_name,
            part_number=part_number,
        )

        results = self.search_client.search(query)

        if not results:
            return self._not_found_response(
                brand_name=brand_name,
                part_number=part_number,
            )

        best_result = self._select_best_result(
            brand_name=brand_name,
            part_number=part_number,
            results=results,
        )

        if not best_result:
            return self._not_found_response(
                brand_name=brand_name,
                part_number=part_number,
            )

        combined_text = self._combine_result_text(best_result)

        price_data = self._extract_price(combined_text)

        product_name = self._clean_product_name(
            title=best_result.title,
            brand_name=brand_name,
            part_number=part_number,
        )

        description = self._build_description(
            result_text=combined_text,
            brand_name=brand_name,
            part_number=part_number,
        )

        return {
            "part_number": str(part_number).strip().upper(),
            "brand": brand_name,
            "product_name": product_name,
            "description": description,
            "market_price": price_data["price"],
            "currency": price_data["currency"] or settings.DEFAULT_CURRENCY,
            "source_url": best_result.link,
            "lookup_status": "found",
        }

    def lookup_market_price(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> dict[str, Any]:
        query = self._build_price_query(
            brand_name=brand_name,
            part_number=part_number,
            product_name=product_name,
        )

        results = self.search_client.search(query)

        if not results:
            return self._price_not_available_response()

        for result in results:
            result_text = self._combine_result_text(result)

            if not self._result_matches_part(
                text=result_text,
                brand_name=brand_name,
                part_number=part_number,
            ):
                continue

            price_data = self._extract_price(result_text)

            if price_data["price"] is not None:
                return {
                    "market_price": price_data["price"],
                    "currency": price_data["currency"] or settings.DEFAULT_CURRENCY,
                    "source_url": result.link,
                    "lookup_status": "price_found",
                }

        return self._price_not_available_response()

    def _build_new_part_query(
        self,
        brand_name: str,
        part_number: str,
    ) -> str:
        return (
            f'"{brand_name}" "{part_number}" laptop spare part '
            f'price description'
        )

    def _build_price_query(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> str:
        if product_name:
            return (
                f'"{brand_name}" "{part_number}" "{product_name}" '
                f'laptop spare part price'
            )

        return (
            f'"{brand_name}" "{part_number}" laptop spare part price'
        )

    def _select_best_result(
        self,
        brand_name: str,
        part_number: str,
        results,
    ):
        for result in results:
            text = self._combine_result_text(result)

            if self._result_matches_part(
                text=text,
                brand_name=brand_name,
                part_number=part_number,
            ):
                return result

        return results[0] if results else None

    def _result_matches_part(
        self,
        text: str,
        brand_name: str,
        part_number: str,
    ) -> bool:
        normalized_text = text.lower()
        normalized_brand = brand_name.lower().strip()
        normalized_part = part_number.lower().strip()

        has_part_number = normalized_part in normalized_text
        has_brand = normalized_brand in normalized_text

        return has_part_number and has_brand

    def _combine_result_text(self, result) -> str:
        return " ".join(
            [
                result.title or "",
                result.snippet or "",
                result.link or "",
            ]
        ).strip()

    def _extract_price(self, text: str) -> dict[str, Any]:
        """
        Extracts prices like:
        $45.99
        USD 45.99
        ₹2500
        INR 2500
        Rs. 2500
        EUR 30.50
        GBP 25
        """

        patterns = [
            (r"\$\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "USD"),
            (r"USD\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "USD"),
            (r"₹\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "INR"),
            (r"INR\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "INR"),
            (r"Rs\.?\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "INR"),
            (r"EUR\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "EUR"),
            (r"€\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "EUR"),
            (r"GBP\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "GBP"),
            (r"£\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)", "GBP"),
        ]

        for pattern, currency in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)

            if match:
                price_text = match.group(1).replace(",", "")

                try:
                    return {
                        "price": round(float(price_text), 2),
                        "currency": currency,
                    }
                except ValueError:
                    continue

        return {
            "price": None,
            "currency": settings.DEFAULT_CURRENCY,
        }

    def _clean_product_name(
        self,
        title: str | None,
        brand_name: str,
        part_number: str,
    ) -> str:
        if not title:
            return f"{brand_name} Laptop Spare Part - {part_number}"

        product_name = title.strip()

        remove_parts = [
            "|",
            "- eBay",
            "- Amazon",
            "- Walmart",
            "- AliExpress",
        ]

        for item in remove_parts:
            if item in product_name:
                product_name = product_name.split(item)[0].strip()

        return product_name[:255]

    def _build_description(
        self,
        result_text: str,
        brand_name: str,
        part_number: str,
    ) -> str:
        cleaned = " ".join(result_text.split())

        if not cleaned:
            return f"{brand_name} laptop spare part for part number {part_number}"

        return cleaned[:1000]

    def _not_found_response(
        self,
        brand_name: str,
        part_number: str,
    ) -> dict[str, Any]:
        return {
            "part_number": str(part_number).strip().upper(),
            "brand": brand_name,
            "product_name": "Not Found",
            "description": "Not Found",
            "market_price": None,
            "currency": settings.DEFAULT_CURRENCY,
            "source_url": None,
            "lookup_status": "not_found",
        }

    def _price_not_available_response(self) -> dict[str, Any]:
        return {
            "market_price": None,
            "currency": settings.DEFAULT_CURRENCY,
            "source_url": None,
            "lookup_status": "price_not_available",
        }