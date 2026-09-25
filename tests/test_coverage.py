"""The SDK calls exactly the operations in Duta's OpenAPI spec, no more and no fewer."""

from __future__ import annotations

import re

from .conftest import EMAIL


def test_calls_exactly_the_operations_in_the_spec(sync_client, spec):
    d, rec = sync_client()

    d.emails.send(EMAIL)
    d.emails.get("msg_1")
    d.emails.list()
    d.batch.send([EMAIL])
    d.domains.create({"name": "kedai.my"})
    d.domains.list()
    d.domains.get("dom_1")
    d.domains.verify("dom_1")
    d.domains.remove("dom_1")
    d.api_keys.create({"name": "CI"})
    d.api_keys.list()
    d.api_keys.remove("key_1")
    d.webhooks.create({"endpoint": "https://kedai.my/hook"})
    d.webhooks.list()
    d.webhooks.get("whk_1")
    d.webhooks.remove("whk_1")
    d.webhooks.enable("whk_1")
    d.webhooks.test("whk_1")
    d.webhooks.deliveries("whk_1")
    d.suppressions.list()
    d.suppressions.create("gone@example.com")
    d.suppressions.remove("gone@example.com")
    d.logs.list()
    d.logs.get("req_1")
    d.usage.get()

    templates = list(spec["paths"])
    made = set()
    for req in rec.requests:
        path = re.sub(r"^/v1", "", req.url.path)
        match = next(
            (t for t in templates if re.fullmatch(re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(t)), path)),
            f"UNKNOWN {path}",
        )
        made.add(f"{req.method.lower()} {match}")

    in_spec = {f"{m} {p}" for p, ops in spec["paths"].items() for m in ops}
    # The archived body is the dashboard's preview, not something an SDK user needs.
    in_spec.discard("get /emails/{id}/body")

    assert sorted(made) == sorted(in_spec)
