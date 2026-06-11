import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def normalize_part_number(part_number: str) -> str:
    return str(part_number).strip().upper()


def is_allowed_file(filename: str) -> bool:
    allowed_extensions = [".xlsx", ".csv"]
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)


def to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def calculate_price_difference(
    current_price: Decimal | None,
    previous_price: Decimal | None,
) -> Decimal | None:
    if current_price is None or previous_price is None:
        return None
    return current_price - previous_price
