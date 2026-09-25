"""Verify a webhook delivery from Duta.

Deliveries are signed per the Standard Webhooks spec, as Resend's are:
HMAC-SHA256 over ``id.timestamp.body``, keyed with the base64 part of the
``whsec_`` secret, sent as ``v1,<base64>``.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any, Mapping

from ._errors import WebhookVerificationError


def verify(
    payload: str | bytes,
    headers: Mapping[str, Any],
    secret: str,
    *,
    tolerance_seconds: int = 300,
) -> dict[str, Any]:
    """Return the event when the signature is valid and recent.

    ``payload`` is the raw request body, before JSON parsing. ``headers`` is
    the request's headers, in any case (webhook-* or svix-*). Raises
    WebhookVerificationError otherwise.
    """
    h = {str(k).lower(): (v[0] if isinstance(v, (list, tuple)) else v) for k, v in headers.items()}
    msg_id = h.get("webhook-id") or h.get("svix-id")
    timestamp = h.get("webhook-timestamp") or h.get("svix-timestamp")
    signature = h.get("webhook-signature") or h.get("svix-signature")
    if not msg_id or not timestamp or not signature:
        raise WebhookVerificationError("Missing webhook-id, webhook-timestamp or webhook-signature header")

    if not str(timestamp).isdigit() or abs(time.time() - int(timestamp)) > tolerance_seconds:
        raise WebhookVerificationError("Timestamp is outside the allowed window")

    raw = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    try:
        key = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise WebhookVerificationError("Signing secret is not valid") from exc

    body = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    mac = hmac.new(key, f"{msg_id}.{timestamp}.{body}".encode("utf-8"), hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("ascii")

    # Several signatures may be sent, space separated, during a secret rotation.
    for part in str(signature).split(" "):
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            try:
                event = json.loads(body)
            except ValueError as exc:
                raise WebhookVerificationError("Payload is not JSON") from exc
            if not isinstance(event, dict):
                raise WebhookVerificationError("Payload is not a JSON object")
            return event
    raise WebhookVerificationError("Signature does not match")
