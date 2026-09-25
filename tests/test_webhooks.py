"""The fixture is a delivery signed by Duta's own webhook signer, so these check
the SDK against what Duta sends. The clock is set to when it was signed."""

from __future__ import annotations

import pytest

from duta import Duta, WebhookVerificationError, verify_webhook


@pytest.fixture
def at(monkeypatch):
    def set_clock(seconds: float) -> None:
        monkeypatch.setattr("duta._webhooks.time.time", lambda: seconds)

    return set_clock


def test_accepts_a_delivery_signed_by_duta(webhook_fixture, at):
    f = webhook_fixture
    at(f["timestamp"] + 10)
    assert verify_webhook(f["body"], f["headers"], f["secret"])["type"] == "email.delivered"


def test_reads_svix_headers_any_case_bytes_and_the_client_method(webhook_fixture, at):
    f = webhook_fixture
    at(f["timestamp"])
    h = f["headers"]
    svix = {"Svix-Id": h["svix-id"], "Svix-Timestamp": h["svix-timestamp"], "Svix-Signature": [h["svix-signature"]]}
    assert verify_webhook(f["body"].encode(), svix, f["secret"])["type"] == "email.delivered"
    assert Duta("k").webhooks.verify(f["body"], h, f["secret"])["type"] == "email.delivered"


def test_refuses_a_body_changed_after_signing(webhook_fixture, at):
    f = webhook_fixture
    at(f["timestamp"])
    with pytest.raises(WebhookVerificationError):
        verify_webhook(f["body"].replace("delivered", "bounced"), f["headers"], f["secret"])


def test_refuses_the_wrong_secret(webhook_fixture, at):
    f = webhook_fixture
    at(f["timestamp"])
    with pytest.raises(WebhookVerificationError, match="does not match"):
        verify_webhook(f["body"], f["headers"], "whsec_" + "cd34" * 8)


def test_refuses_an_old_delivery(webhook_fixture, at):
    f = webhook_fixture
    at(f["timestamp"] + 3600)
    with pytest.raises(WebhookVerificationError, match="outside the allowed window"):
        verify_webhook(f["body"], f["headers"], f["secret"])


def test_refuses_a_delivery_with_no_signature_headers(webhook_fixture):
    with pytest.raises(WebhookVerificationError, match="Missing"):
        verify_webhook(webhook_fixture["body"], {}, webhook_fixture["secret"])
