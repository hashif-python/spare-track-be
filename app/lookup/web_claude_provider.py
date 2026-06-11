from typing import Any

from langchain_anthropic import ChatAnthropic
from pydantic import ValidationError

from app.config import settings
from app.lookup.base import BaseLookupProvider
from app.lookup.schemas import (
    MarketPriceBatchLookupOutput,
    MarketPriceLookupOutput,
    NewPartBatchLookupOutput,
    NewPartLookupOutput,
)
from app.lookup.search import WebSearchClient


class WebClaudeLookupProvider(BaseLookupProvider):
    def __init__(self) -> None:
        self.search_client = WebSearchClient()
        self.llm = self._create_llm()

    def lookup_new_part(
        self,
        brand_name: str,
        part_number: str,
    ) -> dict[str, Any]:
        batch_result = self.lookup_new_parts_batch(
            brand_name=brand_name,
            part_numbers=[part_number],
        )

        return batch_result.get(
            part_number.strip().upper(),
            self._new_part_not_found(
                brand_name=brand_name,
                part_number=part_number,
                reason="No result returned from batch lookup",
            ),
        )

    def lookup_market_price(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> dict[str, Any]:
        batch_result = self.lookup_market_prices_batch(
            brand_name=brand_name,
            parts=[
                {
                    "part_number": part_number,
                    "product_name": product_name,
                }
            ],
        )

        return batch_result.get(
            part_number.strip().upper(),
            self._price_not_available(
                part_number=part_number,
                reason="No result returned from batch lookup",
            ),
        )

    def lookup_new_parts_batch(
        self,
        brand_name: str,
        part_numbers: list[str],
    ) -> dict[str, dict[str, Any]]:
        cleaned_part_numbers = self._clean_part_numbers(part_numbers)

        if not cleaned_part_numbers:
            return {}

        if not settings.ANTHROPIC_API_KEY:
            return {
                part_number: self._new_part_not_found(
                    brand_name=brand_name,
                    part_number=part_number,
                    reason="ANTHROPIC_API_KEY is missing",
                )
                for part_number in cleaned_part_numbers
            }

        final_results: dict[str, dict[str, Any]] = {}

        for batch in self._chunk_list(cleaned_part_numbers, settings.LOOKUP_BATCH_SIZE):
            evidence = self.search_client.search_parts_batch(
                brand_name=brand_name,
                part_numbers=batch,
            )

            search_context = self.search_client.format_batch_for_llm(evidence)

            prompt = self._build_new_parts_batch_prompt(
                brand_name=brand_name,
                part_numbers=batch,
                search_context=search_context,
            )

            try:
                structured_llm = self.llm.with_structured_output(NewPartBatchLookupOutput)
                response = structured_llm.invoke(prompt)

                if isinstance(response, NewPartBatchLookupOutput):
                    validated = response
                else:
                    validated = NewPartBatchLookupOutput.model_validate(response)

                batch_results = self._validate_new_parts_batch_result(
                    brand_name=brand_name,
                    expected_part_numbers=batch,
                    result=validated,
                )

                final_results.update(batch_results)

            except ValidationError as exc:
                for part_number in batch:
                    final_results[part_number] = self._new_part_not_found(
                        brand_name=brand_name,
                        part_number=part_number,
                        reason=f"Batch validation failed: {str(exc)}",
                    )

            except Exception as exc:
                for part_number in batch:
                    final_results[part_number] = self._new_part_not_found(
                        brand_name=brand_name,
                        part_number=part_number,
                        reason=f"Claude batch lookup failed: {str(exc)}",
                    )

        return final_results

    def lookup_market_prices_batch(
        self,
        brand_name: str,
        parts: list[dict[str, str | None]],
    ) -> dict[str, dict[str, Any]]:
        cleaned_parts = self._clean_price_parts(parts)

        if not cleaned_parts:
            return {}

        if not settings.ANTHROPIC_API_KEY:
            return {
                item["part_number"]: self._price_not_available(
                    part_number=item["part_number"],
                    reason="ANTHROPIC_API_KEY is missing",
                )
                for item in cleaned_parts
            }

        final_results: dict[str, dict[str, Any]] = {}

        for batch in self._chunk_list(cleaned_parts, settings.LOOKUP_BATCH_SIZE):
            evidence = self.search_client.search_price_batch(
                brand_name=brand_name,
                parts=batch,
            )

            search_context = self.search_client.format_batch_for_llm(evidence)

            prompt = self._build_prices_batch_prompt(
                brand_name=brand_name,
                parts=batch,
                search_context=search_context,
            )

            try:
                structured_llm = self.llm.with_structured_output(MarketPriceBatchLookupOutput)
                response = structured_llm.invoke(prompt)

                if isinstance(response, MarketPriceBatchLookupOutput):
                    validated = response
                else:
                    validated = MarketPriceBatchLookupOutput.model_validate(response)

                batch_results = self._validate_prices_batch_result(
                    expected_parts=batch,
                    result=validated,
                )

                final_results.update(batch_results)

            except ValidationError as exc:
                for item in batch:
                    part_number = item["part_number"]
                    final_results[part_number] = self._price_not_available(
                        part_number=part_number,
                        reason=f"Batch validation failed: {str(exc)}",
                    )

            except Exception as exc:
                for item in batch:
                    part_number = item["part_number"]
                    final_results[part_number] = self._price_not_available(
                        part_number=part_number,
                        reason=f"Claude batch price lookup failed: {str(exc)}",
                    )

        return final_results

    def _create_llm(self) -> ChatAnthropic:
        return ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            temperature=0,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
            timeout=settings.LOOKUP_TIMEOUT_SECONDS,
            max_retries=2,
            api_key=settings.ANTHROPIC_API_KEY,
        )

    def _build_new_parts_batch_prompt(
        self,
        brand_name: str,
        part_numbers: list[str],
        search_context: str,
    ) -> str:
        part_numbers_text = ", ".join(part_numbers)

        return f"""
You are a laptop spare parts research assistant.

Goal:
Find product name, description, and market price for many laptop spare parts in ONE response.

Brand:
{brand_name}

Part Numbers:
{part_numbers_text}

Web Search Evidence:
{search_context}

Return structured output only.

Required response shape:
{{
  "results": [
    {{
      "part_number": "EXACT_PART_NUMBER",
      "brand": "{brand_name}",
      "product_name": "Product name or Not Found",
      "description": "Short useful description or Not Found",
      "market_price": 49.99,
      "currency": "USD",
      "source_url": "https://source-url.com",
      "lookup_status": "found",
      "confidence": 0.85
    }}
  ]
}}

Rules:
1. Return one result for every requested part number.
2. Use only the supplied web evidence.
3. Do not invent product name, price, URL, or description.
4. If exact part number is not clearly found, use lookup_status = "not_found".
5. If not found, product_name = "Not Found" and description = "Not Found".
6. market_price must be numeric only or null.
7. source_url must be from the supplied evidence.
8. confidence must be between 0 and 1.
9. Use confidence >= 0.8 only when exact brand and exact part number are found.
10. Use confidence below 0.65 when only similar part numbers are found.
"""

    def _build_prices_batch_prompt(
        self,
        brand_name: str,
        parts: list[dict[str, str | None]],
        search_context: str,
    ) -> str:
        part_lines = []

        for item in parts:
            part_lines.append(
                f"- part_number: {item['part_number']}, product_name: {item.get('product_name') or 'Unknown'}"
            )

        parts_text = "\n".join(part_lines)

        return f"""
You are a laptop spare parts market price extraction assistant.

Goal:
Find latest reliable market price for many laptop spare parts in ONE response.

Brand:
{brand_name}

Parts:
{parts_text}

Web Search Evidence:
{search_context}

Return structured output only.

Required response shape:
{{
  "results": [
    {{
      "part_number": "EXACT_PART_NUMBER",
      "market_price": 49.99,
      "currency": "USD",
      "source_url": "https://source-url.com",
      "lookup_status": "price_found",
      "confidence": 0.85
    }}
  ]
}}

Rules:
1. Return one result for every requested part number.
2. Use only supplied web evidence.
3. Do not invent price.
4. If no clear price is found, use lookup_status = "price_not_available".
5. market_price must be numeric only or null.
6. source_url must be from supplied evidence.
7. confidence must be between 0 and 1.
8. Use confidence >= 0.8 only when exact brand and exact part number are found.
9. Do not use price if result is for a different part number.
"""

    def _validate_new_parts_batch_result(
        self,
        brand_name: str,
        expected_part_numbers: list[str],
        result: NewPartBatchLookupOutput,
    ) -> dict[str, dict[str, Any]]:
        expected = {part_number.upper() for part_number in expected_part_numbers}

        results_by_part: dict[str, dict[str, Any]] = {}

        for item in result.results:
            part_number = item.part_number.strip().upper()

            if part_number not in expected:
                continue

            if item.lookup_status != "found":
                results_by_part[part_number] = self._new_part_not_found(
                    brand_name=brand_name,
                    part_number=part_number,
                    reason="Lookup status was not_found",
                )
                continue

            if item.confidence < settings.LOOKUP_MIN_CONFIDENCE:
                results_by_part[part_number] = self._new_part_not_found(
                    brand_name=brand_name,
                    part_number=part_number,
                    reason=f"Low confidence: {item.confidence}",
                )
                continue

            if not item.product_name or item.product_name.strip().lower() == "not found":
                results_by_part[part_number] = self._new_part_not_found(
                    brand_name=brand_name,
                    part_number=part_number,
                    reason="Product name missing",
                )
                continue

            results_by_part[part_number] = {
                "part_number": part_number,
                "brand": item.brand.strip() or brand_name,
                "product_name": item.product_name.strip(),
                "description": item.description.strip(),
                "market_price": item.market_price,
                "currency": item.currency,
                "source_url": item.source_url,
                "lookup_status": "found",
                "confidence": item.confidence,
            }

        for part_number in expected:
            if part_number not in results_by_part:
                results_by_part[part_number] = self._new_part_not_found(
                    brand_name=brand_name,
                    part_number=part_number,
                    reason="No result returned for this part number",
                )

        return results_by_part

    def _validate_prices_batch_result(
        self,
        expected_parts: list[dict[str, str | None]],
        result: MarketPriceBatchLookupOutput,
    ) -> dict[str, dict[str, Any]]:
        expected = {item["part_number"].upper() for item in expected_parts}

        results_by_part: dict[str, dict[str, Any]] = {}

        for item in result.results:
            part_number = item.part_number.strip().upper()

            if part_number not in expected:
                continue

            if item.lookup_status != "price_found":
                results_by_part[part_number] = self._price_not_available(
                    part_number=part_number,
                    reason="Lookup status was price_not_available",
                )
                continue

            if item.confidence < settings.LOOKUP_MIN_CONFIDENCE:
                results_by_part[part_number] = self._price_not_available(
                    part_number=part_number,
                    reason=f"Low confidence: {item.confidence}",
                )
                continue

            if item.market_price is None:
                results_by_part[part_number] = self._price_not_available(
                    part_number=part_number,
                    reason="Market price missing",
                )
                continue

            results_by_part[part_number] = {
                "part_number": part_number,
                "market_price": item.market_price,
                "currency": item.currency,
                "source_url": item.source_url,
                "lookup_status": "price_found",
                "confidence": item.confidence,
            }

        for part_number in expected:
            if part_number not in results_by_part:
                results_by_part[part_number] = self._price_not_available(
                    part_number=part_number,
                    reason="No result returned for this part number",
                )

        return results_by_part

    def _new_part_not_found(
        self,
        brand_name: str,
        part_number: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        description = "Not Found"

        if settings.DEBUG and reason:
            description = f"Not Found - {reason}"

        return {
            "part_number": str(part_number).strip().upper(),
            "brand": brand_name,
            "product_name": "Not Found",
            "description": description,
            "market_price": None,
            "currency": settings.DEFAULT_CURRENCY,
            "source_url": None,
            "lookup_status": "not_found",
            "confidence": 0,
        }

    def _price_not_available(
        self,
        part_number: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        response = {
            "part_number": str(part_number).strip().upper(),
            "market_price": None,
            "currency": settings.DEFAULT_CURRENCY,
            "source_url": None,
            "lookup_status": "price_not_available",
            "confidence": 0,
        }

        if settings.DEBUG and reason:
            response["debug_reason"] = reason

        return response

    def _clean_part_numbers(self, part_numbers: list[str]) -> list[str]:
        cleaned = []

        for part_number in part_numbers:
            value = str(part_number).strip().upper()

            if value and value not in cleaned:
                cleaned.append(value)

        return cleaned

    def _clean_price_parts(
        self,
        parts: list[dict[str, str | None]],
    ) -> list[dict[str, str | None]]:
        cleaned = []
        seen = set()

        for item in parts:
            part_number = str(item.get("part_number") or "").strip().upper()

            if not part_number or part_number in seen:
                continue

            seen.add(part_number)

            cleaned.append(
                {
                    "part_number": part_number,
                    "product_name": item.get("product_name"),
                }
            )

        return cleaned

    def _chunk_list(self, items: list, size: int) -> list[list]:
        if size <= 0:
            size = 10

        return [items[index : index + size] for index in range(0, len(items), size)]