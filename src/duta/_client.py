from __future__ import annotations

from typing import Any, Optional

import httpx

from ._http import AsyncHttp, SyncHttp
from ._resources import (
    ApiKeys,
    AsyncEmails,
    AsyncLogs,
    AsyncSuppressions,
    Batch,
    Domains,
    SyncEmails,
    SyncLogs,
    SyncSuppressions,
    Usage,
    Webhooks,
)


class Duta:
    """The Duta client.

    >>> duta = Duta()  # reads DUTA_API_KEY
    >>> sent = duta.emails.send({"from": "Kedai <resit@kedai.my>", "to": "siti@example.com",
    ...                          "subject": "Resit", "html": "<p>Terima kasih.</p>"})

    Every method returns the API's JSON as a dict and raises DutaError on an error.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: Optional[httpx.Client] = None,
        **internal: Any,
    ) -> None:
        self._http = SyncHttp(api_key, base_url, timeout, max_retries, http_client, **internal)
        request = self._http.request
        self.emails = SyncEmails(request)
        self.batch = Batch(request)
        self.domains = Domains(request)
        self.api_keys = ApiKeys(request)
        self.webhooks = Webhooks(request)
        self.suppressions = SyncSuppressions(request)
        self.logs = SyncLogs(request)
        self.usage = Usage(request)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Duta":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncDuta:
    """The Duta client for asyncio. Every method is awaited:

    >>> async with AsyncDuta() as duta:
    ...     sent = await duta.emails.send({...})
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: Optional[httpx.AsyncClient] = None,
        **internal: Any,
    ) -> None:
        self._http = AsyncHttp(api_key, base_url, timeout, max_retries, http_client, **internal)
        request = self._http.request
        self.emails = AsyncEmails(request)
        self.batch = Batch(request)
        self.domains = Domains(request)
        self.api_keys = ApiKeys(request)
        self.webhooks = Webhooks(request)
        self.suppressions = AsyncSuppressions(request)
        self.logs = AsyncLogs(request)
        self.usage = Usage(request)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncDuta":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
