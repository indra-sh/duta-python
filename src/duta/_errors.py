from __future__ import annotations

from typing import Any, Optional


class DutaError(Exception):
    """An error from the Duta API, or from reaching it.

    ``code`` is Duta's error code (https://docs.duta.indra.sh/guides/errors/),
    ``name`` the Resend-compatible name and ``request_id`` finds the request on
    the Logs screen. ``status_code`` is None when Duta could not be reached.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int],
        name: str,
        code: str,
        request_id: Optional[str],
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.name = name
        self.code = code
        self.request_id = request_id
        self.detail = detail

    def __repr__(self) -> str:
        return f"DutaError(status_code={self.status_code!r}, code={self.code!r}, message={self.message!r}, request_id={self.request_id!r})"


class WebhookVerificationError(Exception):
    """The delivery is not from Duta, was changed or is too old. Never trust its body."""
