"""Authentication, timeouts, retries and the error shape, for both clients.

A 429 is retried for any request, after Retry-After. A 5xx or a network
failure is retried only when the request is safe to repeat, since the first
attempt may have taken effect.
"""

from __future__ import annotations

import asyncio
import email.utils
import json
import os
import random
import time
import uuid
from typing import Any, Callable, Mapping, Optional

import httpx

from ._errors import DutaError
from ._version import __version__

DEFAULT_BASE_URL = "https://api.duta.indra.sh"


def new_idempotency_key() -> str:
    """A fresh key per call, so the SDK's own retries can never send twice."""
    return f"duta-python-{uuid.uuid4()}"


class _Base:
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
    ) -> None:
        key = api_key or os.environ.get("DUTA_API_KEY")
        if not key:
            raise ValueError("Missing API key. Pass it to Duta(api_key) or set DUTA_API_KEY.")
        self._key = key
        self._base_url = (base_url or os.environ.get("DUTA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._max_retries = max(0, max_retries)

    def _prepare(
        self,
        path: str,
        query: Optional[Mapping[str, Any]],
        headers: Optional[Mapping[str, Optional[str]]],
        body: Any,
    ) -> tuple[str, dict[str, Any], dict[str, str], Optional[bytes]]:
        params = {k: v for k, v in (query or {}).items() if v is not None and v != ""}
        sent = {
            "Authorization": f"Bearer {self._key}",
            "User-Agent": f"duta-python/{__version__}",
            "Accept": "application/json",
        }
        for name, value in (headers or {}).items():
            if value is not None:
                sent[name] = value
        content = None
        if body is not None:
            content = json.dumps(body, ensure_ascii=False).encode("utf-8")
            sent["Content-Type"] = "application/json"
        return f"{self._base_url}/v1{path}", params, sent, content

    def _should_retry(self, status: int, idempotent: bool, attempt: int) -> bool:
        return attempt < self._max_retries and (status == 429 or (status >= 500 and idempotent))

    @staticmethod
    def _backoff(attempt: int) -> float:
        base = min(8.0, 0.5 * 2**attempt)
        return base / 2 + random.random() * base / 2

    @staticmethod
    def _retry_after(response: httpx.Response) -> Optional[float]:
        header = response.headers.get("retry-after")
        if not header:
            return None
        try:
            return min(float(header), 60.0)
        except ValueError:
            parsed = email.utils.parsedate_to_datetime(header)
            return max(0.0, min(parsed.timestamp() - time.time(), 60.0)) if parsed else None

    @staticmethod
    def _result(response: httpx.Response) -> Any:
        text = response.text
        try:
            data = json.loads(text) if text else {}
        except ValueError:
            data = None
        if 200 <= response.status_code < 300:
            return data if data is not None else {}
        error = data if isinstance(data, dict) else {}
        raise DutaError(
            str(error.get("message") or f"Duta answered {response.status_code}"),
            status_code=response.status_code,
            name=str(error.get("name") or "application_error"),
            code=str(error.get("code") or "internal_error"),
            request_id=error.get("request_id") or response.headers.get("x-request-id"),
            detail=error.get("detail") if isinstance(error.get("detail"), dict) else None,
        )

    @staticmethod
    def _unreachable(exc: Exception) -> DutaError:
        timed_out = isinstance(exc, httpx.TimeoutException)
        return DutaError(
            "Duta did not answer in time" if timed_out else f"Could not reach Duta: {exc}",
            status_code=None,
            name="timeout" if timed_out else "network_error",
            code="timeout" if timed_out else "network_error",
            request_id=None,
        )


class SyncHttp(_Base):
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: Optional[httpx.Client] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries)
        self._client = http_client or httpx.Client(timeout=timeout)
        self._sleep = sleep

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        body: Any = None,
        headers: Optional[Mapping[str, Optional[str]]] = None,
        idempotent: bool = False,
    ) -> Any:
        url, params, sent, content = self._prepare(path, query, headers, body)
        attempt = 0
        while True:
            try:
                response = self._client.request(method, url, params=params, headers=sent, content=content)
            except httpx.TransportError as exc:
                if idempotent and attempt < self._max_retries:
                    self._sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise self._unreachable(exc) from exc
            if self._should_retry(response.status_code, idempotent, attempt):
                wait = self._retry_after(response)
                self._sleep(wait if wait is not None else self._backoff(attempt))
                attempt += 1
                continue
            return self._result(response)

    def close(self) -> None:
        self._client.close()


class AsyncHttp(_Base):
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: Optional[httpx.AsyncClient] = None,
        sleep: Optional[Callable[[float], Any]] = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries)
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._sleep = sleep or asyncio.sleep

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        body: Any = None,
        headers: Optional[Mapping[str, Optional[str]]] = None,
        idempotent: bool = False,
    ) -> Any:
        url, params, sent, content = self._prepare(path, query, headers, body)
        attempt = 0
        while True:
            try:
                response = await self._client.request(method, url, params=params, headers=sent, content=content)
            except httpx.TransportError as exc:
                if idempotent and attempt < self._max_retries:
                    await self._sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise self._unreachable(exc) from exc
            if self._should_retry(response.status_code, idempotent, attempt):
                wait = self._retry_after(response)
                await self._sleep(wait if wait is not None else self._backoff(attempt))
                attempt += 1
                continue
            return self._result(response)

    async def aclose(self) -> None:
        await self._client.aclose()
