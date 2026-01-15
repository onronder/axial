"""
API error helpers for consistent structured responses.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException


def build_error_payload(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return payload


def raise_http_error(status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=build_error_payload(code, message, details),
    )
