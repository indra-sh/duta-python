from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from duta import AsyncDuta, Duta

FIXTURES = Path(__file__).parent / "fixtures"
EMAIL = {"from": "Kedai <resit@kedai.my>", "to": "siti@example.com", "subject": "Resit", "text": "Terima kasih"}


class Recorder:
    """Answers requests from a queue, then with an empty page, and records them."""

    def __init__(self, answers: list[Any] | None = None) -> None:
        self.answers = list(answers or [])
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.answers:
            answer = self.answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer
        return httpx.Response(200, json={"data": [], "has_more": False, "next": None})

    def body(self, i: int) -> Any:
        return json.loads(self.requests[i].content)


def error(status: int, code: str, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        json={"statusCode": status, "name": "x", "message": f"{code} happened", "code": code, "request_id": "req_body"},
        headers={"x-request-id": "req_header", **(headers or {})},
    )


@pytest.fixture
def sync_client():
    def make(answers: list[Any] | None = None, **options: Any) -> tuple[Duta, Recorder]:
        rec = Recorder(answers)
        client = Duta("duta_test", http_client=httpx.Client(transport=httpx.MockTransport(rec)), sleep=lambda s: None, **options)
        return client, rec

    return make


@pytest.fixture
def async_client():
    def make(answers: list[Any] | None = None, **options: Any) -> tuple[AsyncDuta, Recorder]:
        rec = Recorder(answers)

        async def no_sleep(_: float) -> None:
            return None

        client = AsyncDuta(
            "duta_test", http_client=httpx.AsyncClient(transport=httpx.MockTransport(rec)), sleep=no_sleep, **options
        )
        return client, rec

    return make


@pytest.fixture
def spec() -> dict[str, Any]:
    return json.loads((FIXTURES / "openapi.json").read_text())


@pytest.fixture
def webhook_fixture() -> dict[str, Any]:
    return json.loads((FIXTURES / "webhook.json").read_text())
