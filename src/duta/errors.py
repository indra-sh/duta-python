"""Error types for the Duta SDK."""

from __future__ import annotations

from typing import Any, List, Optional

_NAME_BY_STATUS = {
    400: "validation_error",
    401: "authentication_error",
    403: "permission_denied",
    404: "not_found",
    422: "unprocessable_entity",
    429: "rate_limit_exceeded",
    500: "internal_server_error",
}


class DutaError(Exception):
    """Raised when the Duta API returns an error.

    Attributes:
        name: Machine-readable error name, e.g. ``rate_limit_exceeded``.
        message: Human-readable description.
        status_code: HTTP status code (0 for network errors).
        blocked: Suppressed recipient addresses, present on some 422 errors.
    """

    def __init__(self, name: str, message: str, status_code: int, blocked: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.name = name
        self.message = message
        self.status_code = status_code
        self.blocked = blocked

    @classmethod
    def from_response(cls, status_code: int, body: Any) -> "DutaError":
        """Normalise either of Duta's error shapes into a DutaError."""
        fallback = _NAME_BY_STATUS.get(status_code, "api_error")
        if isinstance(body, dict):
            blocked = body.get("blocked") if isinstance(body.get("blocked"), list) else None
            # Rate-limit shape: { statusCode, name, message }
            if isinstance(body.get("name"), str) and isinstance(body.get("message"), str):
                return cls(body["name"], body["message"], status_code, blocked)
            # Common shape: { error: str }
            if isinstance(body.get("error"), str):
                return cls(fallback, body["error"], status_code, blocked)
        return cls(fallback, f"Request failed with status {status_code}", status_code)
