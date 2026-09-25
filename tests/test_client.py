from __future__ import annotations

import re
from urllib.parse import parse_qs

import httpx
import pytest

from duta import Duta, DutaError

from .conftest import EMAIL, error


def test_sends_with_the_key_a_user_agent_and_an_idempotency_key(sync_client):
    duta, rec = sync_client([httpx.Response(202, json={"id": "msg_1", "status": "queued"})])
    assert duta.emails.send(EMAIL) == {"id": "msg_1", "status": "queued"}
    req = rec.requests[0]
    assert req.method == "POST"
    assert str(req.url) == "https://api.duta.indra.sh/v1/emails"
    assert req.headers["authorization"] == "Bearer duta_test"
    assert req.headers["user-agent"].startswith("duta-python/")
    assert re.fullmatch(r"duta-python-[0-9a-f-]{36}", req.headers["idempotency-key"])
    assert rec.body(0) == EMAIL


def test_uses_the_idempotency_key_it_is_given(sync_client):
    duta, rec = sync_client()
    duta.emails.send(EMAIL, idempotency_key="receipt-1042")
    assert rec.requests[0].headers["idempotency-key"] == "receipt-1042"


def test_raises_the_api_error_with_its_code_and_request_id(sync_client):
    duta, _ = sync_client([error(422, "validation_failed")])
    with pytest.raises(DutaError) as exc:
        duta.emails.send(EMAIL)
    assert exc.value.status_code == 422
    assert exc.value.code == "validation_failed"
    assert exc.value.message == "validation_failed happened"
    assert exc.value.request_id == "req_body"


def test_falls_back_to_the_request_id_header(sync_client):
    duta, _ = sync_client([httpx.Response(502, text="upstream broke", headers={"x-request-id": "req_h"})], max_retries=0)
    with pytest.raises(DutaError) as exc:
        duta.domains.list()
    assert (exc.value.status_code, exc.value.request_id) == (502, "req_h")


def test_retries_a_429_for_any_request(sync_client):
    duta, rec = sync_client([error(429, "rate_limited", {"retry-after": "0"}), httpx.Response(201, json={"id": "dom_1"})])
    assert duta.domains.create({"name": "kedai.my"}) == {"id": "dom_1"}
    assert len(rec.requests) == 2


def test_retries_a_send_after_a_5xx_with_the_same_idempotency_key(sync_client):
    duta, rec = sync_client([error(503, "platform_halted"), httpx.Response(202, json={"id": "msg_2"})])
    assert duta.emails.send(EMAIL) == {"id": "msg_2"}
    assert len(rec.requests) == 2
    assert rec.requests[0].headers["idempotency-key"] == rec.requests[1].headers["idempotency-key"]


def test_never_retries_a_5xx_on_a_write_that_may_have_taken_effect(sync_client):
    duta, rec = sync_client([error(500, "internal_error"), httpx.Response(201, json={})])
    with pytest.raises(DutaError) as exc:
        duta.api_keys.create({"name": "CI"})
    assert exc.value.code == "internal_error"
    assert len(rec.requests) == 1


def test_retries_a_read_after_a_network_failure_but_not_a_write(sync_client):
    duta, _ = sync_client([httpx.ConnectError("socket hang up"), httpx.Response(200, json={"id": "msg_3"})])
    assert duta.emails.get("msg_3") == {"id": "msg_3"}

    duta, rec = sync_client([httpx.ConnectError("socket hang up")])
    with pytest.raises(DutaError) as exc:
        duta.webhooks.test("whk_1")
    assert exc.value.status_code is None and exc.value.code == "network_error"
    assert len(rec.requests) == 1


def test_pages_through_every_email_with_list_all(sync_client):
    duta, rec = sync_client([
        httpx.Response(200, json={"data": [{"id": "msg_a"}, {"id": "msg_b"}], "has_more": True, "next": "msg_b"}),
        httpx.Response(200, json={"data": [{"id": "msg_c"}], "has_more": False, "next": None}),
    ])
    assert [e["id"] for e in duta.emails.list_all(limit=2)] == ["msg_a", "msg_b", "msg_c"]
    assert parse_qs(rec.requests[1].url.query.decode()) == {"limit": ["2"], "after": ["msg_b"]}


def test_takes_a_base_url_with_or_without_a_trailing_slash(sync_client):
    duta, rec = sync_client(base_url="http://localhost:8787/")
    duta.usage.get()
    assert str(rec.requests[0].url) == "http://localhost:8787/v1/usage"


def test_refuses_to_start_without_a_key(monkeypatch):
    monkeypatch.delenv("DUTA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Missing API key"):
        Duta()


async def test_the_async_client_sends_retries_and_pages(async_client):
    duta, rec = async_client([
        error(429, "rate_limited", {"retry-after": "0"}),
        httpx.Response(202, json={"id": "msg_async", "status": "queued"}),
        httpx.Response(200, json={"data": [{"id": "msg_a"}], "has_more": True, "next": "msg_a"}),
        httpx.Response(200, json={"data": [{"id": "msg_b"}], "has_more": False, "next": None}),
    ])
    async with duta:
        assert (await duta.emails.send(EMAIL))["id"] == "msg_async"
        assert [e["id"] async for e in duta.emails.list_all()] == ["msg_a", "msg_b"]
    assert rec.requests[0].headers["idempotency-key"] == rec.requests[1].headers["idempotency-key"]


async def test_the_async_client_raises_duta_error(async_client):
    duta, _ = async_client([error(401, "unauthorized")])
    with pytest.raises(DutaError) as exc:
        await duta.usage.get()
    assert exc.value.code == "unauthorized"
