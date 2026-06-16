import httpx

from app.config import settings
from app.lookup.schemas import WebSearchResult


class WebSearchClient:
    def __init__(self) -> None:
        self._cache: dict[str, list[WebSearchResult]] = {}

    def search_part(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> list[WebSearchResult]:
        part_number = str(part_number).strip().upper()

        cache_key = self._make_cache_key(
            brand_name=brand_name,
            part_number=part_number,
            product_name=product_name,
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        queries = self._build_queries(
            brand_name=brand_name,
            part_number=part_number,
            product_name=product_name,
        )

        all_results: list[WebSearchResult] = []
        seen_urls = set()

        max_queries = max(
            1,
            getattr(settings, "LOOKUP_MAX_SEARCH_QUERIES_PER_PART", 1),
        )

        for query in queries[:max_queries]:
            results = self._search_tavily(query=query)

            if settings.USE_SERPAPI_FALLBACK and not results:
                results.extend(self._search_serpapi(query=query))

            for result in results:
                url = result.url or ""

                if url and url in seen_urls:
                    continue

                seen_urls.add(url)
                all_results.append(result)

        final_results = all_results[: settings.TAVILY_MAX_RESULTS]
        self._cache[cache_key] = final_results

        return final_results

    def search_parts_batch(
        self,
        brand_name: str,
        part_numbers: list[str],
    ) -> dict[str, list[WebSearchResult]]:
        evidence: dict[str, list[WebSearchResult]] = {}

        unique_part_numbers = self._unique_values(part_numbers)

        for part_number in unique_part_numbers:
            evidence[part_number] = self.search_part(
                brand_name=brand_name,
                part_number=part_number,
            )

        return evidence

    def search_price_batch(
        self,
        brand_name: str,
        parts: list[dict[str, str | None]],
    ) -> dict[str, list[WebSearchResult]]:
        evidence: dict[str, list[WebSearchResult]] = {}

        cleaned_parts = []
        seen = set()

        for item in parts:
            part_number = str(item.get("part_number") or "").strip().upper()

            if not part_number or part_number in seen:
                continue

            seen.add(part_number)

            cleaned_parts.append(
                {
                    "part_number": part_number,
                    "product_name": item.get("product_name"),
                }
            )

        for item in cleaned_parts:
            part_number = item["part_number"]

            evidence[part_number] = self.search_part(
                brand_name=brand_name,
                part_number=part_number,
                product_name=item.get("product_name"),
            )

        return evidence

    def _build_queries(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> list[str]:
        """
        Keep query generic.

        Good:
        Dell NYR84 description and price
        Dell 247PN description and price
        HP L14384-001 description and price

        Avoid forcing product type:
        laptop, server, PowerEdge, Mini SAS, keyboard, screen, etc.
        """

        brand_name = str(brand_name).strip()
        part_number = str(part_number).strip().upper()

        alternatives = self._alternate_part_numbers(part_number)
        alt_text = " OR ".join(alternatives)

        queries = []

        if product_name:
            queries.append(
                f"{brand_name} {part_number} {product_name} description and price"
            )

        queries.append(f"{brand_name} {part_number} description and price")

        if len(alternatives) > 1:
            queries.append(f"{brand_name} ({alt_text}) description and price")

        queries.append(f"{brand_name} {part_number} part number description price")
        queries.append(f"{brand_name} {part_number} spare part")

        return list(dict.fromkeys(queries))

    def _alternate_part_numbers(self, part_number: str) -> list[str]:
        """
        Dell often uses both:
        Y100N and 0Y100N
        M299P and 0M299P
        86TPR and 086TPR
        """

        part_number = str(part_number).strip().upper()

        alternatives = [part_number]

        if not part_number.startswith("0"):
            alternatives.append(f"0{part_number}")

        if part_number.startswith("0") and len(part_number) > 1:
            alternatives.append(part_number[1:])

        return list(dict.fromkeys(alternatives))

    def _search_tavily(self, query: str) -> list[WebSearchResult]:
        if not settings.TAVILY_API_KEY:
            return []

        url = "https://api.tavily.com/search"

        payload = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": settings.TAVILY_SEARCH_DEPTH,
            "max_results": settings.TAVILY_MAX_RESULTS,
            "include_answer": False,
            "include_raw_content": False,
        }

        try:
            with httpx.Client(timeout=settings.LOOKUP_TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            results: list[WebSearchResult] = []

            for item in data.get("results", []):
                results.append(
                    WebSearchResult(
                        title=item.get("title"),
                        url=item.get("url"),
                        content=item.get("content"),
                    )
                )

            return results

        except Exception:
            return []

    def _search_serpapi(self, query: str) -> list[WebSearchResult]:
        if not settings.SERPAPI_API_KEY:
            return []

        url = "https://serpapi.com/search.json"

        params = {
            "engine": "google",
            "q": query,
            "api_key": settings.SERPAPI_API_KEY,
            "num": settings.TAVILY_MAX_RESULTS,
        }

        try:
            with httpx.Client(timeout=settings.LOOKUP_TIMEOUT_SECONDS) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            results: list[WebSearchResult] = []

            for item in data.get("organic_results", []):
                results.append(
                    WebSearchResult(
                        title=item.get("title"),
                        url=item.get("link"),
                        content=item.get("snippet"),
                    )
                )

            return results

        except Exception:
            return []

    def format_batch_for_llm(
        self,
        evidence: dict[str, list[WebSearchResult]],
    ) -> str:
        if not evidence:
            return "No web search results found."

        blocks: list[str] = []

        for part_number, results in evidence.items():
            lines = [f"REQUESTED PART NUMBER: {part_number}"]

            if not results:
                lines.append("No search results found for this part.")
            else:
                for index, item in enumerate(results, start=1):
                    lines.append(
                        "\n".join(
                            [
                                f"Source {index}:",
                                f"Title: {item.title or 'N/A'}",
                                f"URL: {item.url or 'N/A'}",
                                f"Content: {self._shorten(item.content)}",
                            ]
                        )
                    )

            blocks.append("\n".join(lines))

        return "\n\n---\n\n".join(blocks)

    def _shorten(self, value: str | None, limit: int = 500) -> str:
        if not value:
            return "N/A"

        value = str(value).strip()

        if len(value) <= limit:
            return value

        return value[:limit] + "..."

    def _make_cache_key(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> str:
        return "|".join(
            [
                str(brand_name).strip().lower(),
                str(part_number).strip().upper(),
                str(product_name or "").strip().lower(),
            ]
        )

    def _unique_values(self, values: list[str]) -> list[str]:
        cleaned = []

        for value in values:
            item = str(value).strip().upper()

            if item and item not in cleaned:
                cleaned.append(item)

        return cleaned