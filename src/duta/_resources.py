"""The API's resources. Each method returns the parsed JSON for ``Duta`` and
an awaitable of it for ``AsyncDuta``: the request function decides which."""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Iterator, Literal, Mapping, Optional, Sequence
from urllib.parse import quote

from ._http import new_idempotency_key
from ._types import ApiKeyParams, DomainParams, SendEmailParams, WebhookParams
from ._webhooks import verify

Request = Callable[..., Any]


def _seg(value: str) -> str:
    return quote(value, safe="")


class _Resource:
    def __init__(self, request: Request) -> None:
        self._request = request


class Emails(_Resource):
    def send(self, email: SendEmailParams, *, idempotency_key: Optional[str] = None) -> Any:
        """Send one email. Returns ``{"id": "msg_...", "status": "queued"}``."""
        return self._request(
            "POST", "/emails", body=email,
            headers={"Idempotency-Key": idempotency_key or new_idempotency_key()}, idempotent=True,
        )

    def get(self, id: str) -> Any:
        return self._request("GET", f"/emails/{_seg(id)}", idempotent=True)

    def list(self, **query: Any) -> Any:
        """One page, newest first. Pass ``next`` as ``after`` for the following page.

        Takes ``limit``, ``after``, ``q`` and ``status``."""
        return self._request("GET", "/emails", query=query, idempotent=True)


class Batch(_Resource):
    def send(
        self,
        emails: Sequence[SendEmailParams],
        *,
        idempotency_key: Optional[str] = None,
        validation: Optional[Literal["strict", "permissive"]] = None,
    ) -> Any:
        """Send up to 100 emails. Strict by default: one invalid email and none are sent."""
        return self._request(
            "POST", "/emails/batch", body=list(emails),
            headers={
                "Idempotency-Key": idempotency_key or new_idempotency_key(),
                "x-batch-validation": validation,
            },
            idempotent=True,
        )


class Domains(_Resource):
    def create(self, domain: DomainParams) -> Any:
        """Returns the domain with the DNS records to publish."""
        return self._request("POST", "/domains", body=domain)

    def list(self) -> Any:
        return self._request("GET", "/domains", idempotent=True)

    def get(self, id: str) -> Any:
        return self._request("GET", f"/domains/{_seg(id)}", idempotent=True)

    def verify(self, id: str) -> Any:
        """Check the domain's DNS now rather than waiting for Duta's own check."""
        return self._request("POST", f"/domains/{_seg(id)}/verify", idempotent=True)

    def remove(self, id: str) -> Any:
        return self._request("DELETE", f"/domains/{_seg(id)}", idempotent=True)


class ApiKeys(_Resource):
    def create(self, key: ApiKeyParams) -> Any:
        """The key is in ``token`` and is shown only once."""
        return self._request("POST", "/api-keys", body=key)

    def list(self) -> Any:
        return self._request("GET", "/api-keys", idempotent=True)

    def remove(self, id: str) -> Any:
        return self._request("DELETE", f"/api-keys/{_seg(id)}", idempotent=True)


class Webhooks(_Resource):
    def create(self, webhook: WebhookParams) -> Any:
        """The ``signing_secret`` in the answer is shown only once."""
        return self._request("POST", "/webhooks", body=webhook)

    def list(self) -> Any:
        return self._request("GET", "/webhooks", idempotent=True)

    def get(self, id: str) -> Any:
        return self._request("GET", f"/webhooks/{_seg(id)}", idempotent=True)

    def remove(self, id: str) -> Any:
        return self._request("DELETE", f"/webhooks/{_seg(id)}", idempotent=True)

    def enable(self, id: str) -> Any:
        """Enable an endpoint that failed its way to disabled."""
        return self._request("POST", f"/webhooks/{_seg(id)}/enable", idempotent=True)

    def test(self, id: str) -> Any:
        """Send a signed test event to the endpoint."""
        return self._request("POST", f"/webhooks/{_seg(id)}/test")

    def deliveries(self, id: str, **query: Any) -> Any:
        return self._request("GET", f"/webhooks/{_seg(id)}/deliveries", query=query, idempotent=True)

    @staticmethod
    def verify(
        payload: str | bytes, headers: Mapping[str, Any], secret: str, *, tolerance_seconds: int = 300
    ) -> dict[str, Any]:
        """Check a delivery's signature and return the event, or raise WebhookVerificationError."""
        return verify(payload, headers, secret, tolerance_seconds=tolerance_seconds)


class Suppressions(_Resource):
    def list(self, **query: Any) -> Any:
        return self._request("GET", "/suppressions", query=query, idempotent=True)

    def create(self, email: str) -> Any:
        return self._request("POST", "/suppressions", body={"email": email}, idempotent=True)

    def remove(self, email: str) -> Any:
        """Only manual entries can be removed. Bounces, complaints and unsubscribes are permanent."""
        return self._request("DELETE", f"/suppressions/{_seg(email)}", idempotent=True)


class Logs(_Resource):
    def list(self, **query: Any) -> Any:
        return self._request("GET", "/logs", query=query, idempotent=True)

    def get(self, id: str) -> Any:
        """A request id from an error or the X-Request-Id header."""
        return self._request("GET", f"/logs/{_seg(id)}", idempotent=True)


class Usage(_Resource):
    def get(self) -> Any:
        """This month's usage, the plan's limits and the last 30 days by status."""
        return self._request("GET", "/usage", idempotent=True)


# Paging: the one place the two clients differ in shape.


def _pages(page: Callable[[Optional[str]], dict[str, Any]]) -> Iterator[dict[str, Any]]:
    after: Optional[str] = None
    while True:
        result = page(after)
        yield from result.get("data", [])
        after = result.get("next") if result.get("has_more") else None
        if not after:
            return


async def _apages(page: Callable[[Optional[str]], Any]) -> AsyncIterator[dict[str, Any]]:
    after: Optional[str] = None
    while True:
        result = await page(after)
        for item in result.get("data", []):
            yield item
        after = result.get("next") if result.get("has_more") else None
        if not after:
            return


class SyncEmails(Emails):
    def list_all(self, **query: Any) -> Iterator[dict[str, Any]]:
        """Every email matching the query, page by page."""
        return _pages(lambda after: self.list(**query, after=after))


class AsyncEmails(Emails):
    def list_all(self, **query: Any) -> AsyncIterator[dict[str, Any]]:
        """Every email matching the query, page by page."""
        return _apages(lambda after: self.list(**query, after=after))


class SyncSuppressions(Suppressions):
    def list_all(self, **query: Any) -> Iterator[dict[str, Any]]:
        return _pages(lambda after: self.list(**query, after=after))


class AsyncSuppressions(Suppressions):
    def list_all(self, **query: Any) -> AsyncIterator[dict[str, Any]]:
        return _apages(lambda after: self.list(**query, after=after))


class SyncLogs(Logs):
    def list_all(self, **query: Any) -> Iterator[dict[str, Any]]:
        return _pages(lambda after: self.list(**query, after=after))


class AsyncLogs(Logs):
    def list_all(self, **query: Any) -> AsyncIterator[dict[str, Any]]:
        return _apages(lambda after: self.list(**query, after=after))

