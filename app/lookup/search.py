import httpx

from app.config import settings
from app.lookup.schemas import WebSearchResult


class WebSearchClient:
    def search_part(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> list[WebSearchResult]:
        query_parts = [
            brand_name,
            part_number,
            product_name or "",
            "laptop spare part price description",
        ]

        query = " ".join([part for part in query_parts if part]).strip()

        results = self._search_tavily(query=query)

        if not results and settings.USE_SERPAPI_FALLBACK:
            results = self._search_serpapi(query=query)

        return results

    def search_parts_batch(
        self,
        brand_name: str,
        part_numbers: list[str],
    ) -> dict[str, list[WebSearchResult]]:
        """
        Search web evidence for many part numbers.

        Important:
        - This may still call search API once per part number.
        - But it reduces expensive LLM calls by sending all evidence in one Claude request.
        """

        evidence: dict[str, list[WebSearchResult]] = {}

        for part_number in part_numbers:
            results = self.search_part(
                brand_name=brand_name,
                part_number=part_number,
            )

            evidence[part_number] = results

        return evidence

    def search_price_batch(
        self,
        brand_name: str,
        parts: list[dict[str, str | None]],
    ) -> dict[str, list[WebSearchResult]]:
        evidence: dict[str, list[WebSearchResult]] = {}

        for item in parts:
            part_number = str(item.get("part_number") or "").strip().upper()
            product_name = item.get("product_name")

            if not part_number:
                continue

            results = self.search_part(
                brand_name=brand_name,
                part_number=part_number,
                product_name=product_name,
            )

            evidence[part_number] = results

        return evidence

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
            lines = [f"PART NUMBER: {part_number}"]

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
                                f"Content: {item.content or 'N/A'}",
                            ]
                        )
                    )

            blocks.append("\n".join(lines))

        return "\n\n---\n\n".join(blocks)