# duta-sdk

The official Python SDK for [Duta](https://duta.indra.sh), transactional
email for Malaysia.

- Python 3.9+. One dependency, `httpx`.
- `Duta` for regular code and `AsyncDuta` for asyncio, with the same methods.
- Retries rate limits and server errors safely: every send carries an
  idempotency key, so a retry can never send twice.

## Upgrading from 0.1.x

0.2.0 is a new SDK for Duta's current API, not an update of 0.1.x, which was
written for an earlier version of Duta that no longer runs.

## Install

```sh
pip install duta-sdk
```

## Send an email

```python
from duta import Duta

duta = Duta()  # reads DUTA_API_KEY

sent = duta.emails.send({
    "from": "Kedai <resit@kedai.my>",
    "to": "siti@example.com",
    "subject": "Resit #1042",
    "html": "<p>Terima kasih.</p>",
})
print(sent["id"])
```

Errors raise `duta.DutaError`. `.code` is Duta's
[error code](https://docs.duta.indra.sh/guides/errors/) and `.request_id`
finds the request on the Logs screen.

```python
from duta import DutaError

try:
    duta.emails.send(email, idempotency_key=f"receipt-{order.id}")
except DutaError as e:
    log.error("send failed: %s %s", e.code, e.request_id)
```

## Async

```python
from duta import AsyncDuta

async with AsyncDuta() as duta:
    await duta.emails.send(email)
    async for e in duta.emails.list_all(status="bounced"):
        print(e["id"])
```

## Batch and paging

```python
duta.batch.send([first, second], validation="permissive")

for e in duta.emails.list_all(status="bounced"):
    print(e["id"])
```

## Verify webhooks

```python
from duta import verify_webhook

event = verify_webhook(
    request.body,        # the raw body, before JSON parsing
    request.headers,
    os.environ["DUTA_WEBHOOK_SECRET"],
)
```

It raises `duta.WebhookVerificationError` when the signature is wrong or the
delivery is more than five minutes old.

## Everything else

| | |
|---|---|
| `emails` | `send`, `get`, `list`, `list_all` |
| `batch` | `send` |
| `domains` | `create`, `list`, `get`, `verify`, `remove` |
| `api_keys` | `create`, `list`, `remove` |
| `webhooks` | `create`, `list`, `get`, `remove`, `enable`, `test`, `deliveries`, `verify` |
| `suppressions` | `create`, `list`, `list_all`, `remove` |
| `logs` | `list`, `list_all`, `get` |
| `usage` | `get` |

Options: `Duta(api_key, base_url=..., timeout=30.0, max_retries=2)`.

Full documentation: https://docs.duta.indra.sh
