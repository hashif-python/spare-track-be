from typing import Any


def success_response(message: str = "Success", data: Any = None) -> dict:
    return {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
    }


def error_response(message: str = "Something went wrong", errors: Any = None) -> dict:
    return {
        "success": False,
        "message": message,
        "errors": errors if errors is not None else {},
    }
