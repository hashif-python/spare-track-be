from abc import ABC, abstractmethod
from typing import Any


class BaseLookupProvider(ABC):
    @abstractmethod
    def lookup_new_part(
        self,
        brand_name: str,
        part_number: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def lookup_market_price(
        self,
        brand_name: str,
        part_number: str,
        product_name: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def lookup_new_parts_batch(
        self,
        brand_name: str,
        part_numbers: list[str],
    ) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def lookup_market_prices_batch(
        self,
        brand_name: str,
        parts: list[dict[str, str | None]],
    ) -> dict[str, dict[str, Any]]:
        raise NotImplementedError