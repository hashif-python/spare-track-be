from pathlib import Path
import pandas as pd


ACCEPTED_PART_NUMBER_COLUMNS = [
    "part number",
    "Part Number",
    "PART NUMBER",
    "part_no",
    "part no",
    "part_no.",
    "sku",
    "item code",
]


def normalize_column_name(column_name: str) -> str:
    return str(column_name).strip().lower().replace("_", " ")


def detect_part_number_column(columns: list[str]) -> str | None:
    normalized_allowed = [normalize_column_name(c) for c in ACCEPTED_PART_NUMBER_COLUMNS]
    for column in columns:
        if normalize_column_name(column) in normalized_allowed:
            return column
    return None


def read_uploaded_file(file_path: str) -> pd.DataFrame:
    extension = Path(file_path).suffix.lower()
    if extension == ".xlsx":
        return pd.read_excel(file_path)
    if extension == ".csv":
        return pd.read_csv(file_path)
    raise ValueError("Unsupported file type")


def read_uploaded_file_preview(file_path: str) -> pd.DataFrame:
    return read_uploaded_file(file_path)


def validate_part_number_column(file_path: str) -> str:
    df = read_uploaded_file(file_path)
    if df.empty:
        raise ValueError("Uploaded file is empty")
    part_number_column = detect_part_number_column(list(df.columns))
    if not part_number_column:
        raise ValueError(f"Part number column not found. Accepted column names: {', '.join(ACCEPTED_PART_NUMBER_COLUMNS)}")
    return part_number_column


def clean_part_number(value) -> str | None:
    if value is None:
        return None
    part_number = str(value).strip()
    if not part_number or part_number.lower() in ["nan", "none", "null"]:
        return None
    return part_number.upper()


def safe_string(value) -> str:
    if value is None:
        return ""
    if str(value).lower() in ["nan", "none", "null"]:
        return ""
    return str(value)
