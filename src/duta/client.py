"""The Duta client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Union

from .errors import DutaError

DEFAULT_BASE_URL = "https://api.duta.indra.sh"


class Emails:
    """The ``emails`` resource: send, retrieve, and list emails."""

    def __init__(self, client: "Duta") -> None:
        self._client = client

    def send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a transactional email.

        Example::

            duta.emails.send({
                "from": "hello@yourdomain.com",
                "to": "user@example.com",
                "subject": "Welcome",
                "html": "<p>Thanks for signing up!</p>",
            })

        Accepts ``from``, ``to``, ``subject``, ``html``, ``text``, ``reply_to``,
        and ``tags``. Returns a dict with ``id`` and ``status``.
        Raises :class:`DutaError` on failure.
        """
        body: Dict[str, Any] = {
            "from": params["from"],
            "to": params["to"],
            "subject": params["subject"],
        }
        if params.get("html") is not None:
            body["html"] = params["html"]
        if params.get("text") is not None:
            body["text"] = params["text"]
        if params.get("reply_to") is not None:
            body["replyTo"] = params["reply_to"]
        if params.get("tags") is not None:
            body["tags"] = params["tags"]
        return self._client._request("POST", "/v1/email/send", body)

    def get(self, email_id: str) -> Dict[str, Any]:
        """Retrieve a single email by ID. Requires a full-access API key."""
        return self._client._request("GET", f"/v1/email/{email_id}")

    def list(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """List emails, most recent first. Requires a full-access API key."""
        return self._client._request("GET", f"/v1/email?page={page}&limit={limit}")


class Duta:
    """Duta API client.

    Example::

        from duta import Duta

        duta = Duta("duta_live_xxx")
        duta.emails.send({
            "from": "hello@yourdomain.com",
            "to": "user@example.com",
            "subject": "Hello",
            "text": "It works!",
        })
    """

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0) -> None:
        if not api_key:
            raise ValueError("A Duta API key is required. Create one at https://app.duta.indra.sh.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self.emails = Emails(self)

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = None
            raise DutaError.from_response(exc.code, parsed) from None
        except urllib.error.URLError as exc:
            raise DutaError("network_error", str(exc.reason), 0) from None
