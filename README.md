# Duta Python SDK

Official Python client for [Duta](https://duta.indra.sh). Zero dependencies, standard library only.

## Install

```bash
pip install duta-sdk
```

## Quickstart

```python
from duta import Duta

duta = Duta("duta_live_xxx")

result = duta.emails.send({
    "from": "hello@yourdomain.com",
    "to": "user@example.com",
    "subject": "Welcome to Duta",
    "html": "<p>Thanks for signing up!</p>",
})
print("Sent:", result["id"])
```

Get an API key from the [dashboard](https://app.duta.indra.sh). The sender domain must be verified first.

## Error handling

Methods raise `DutaError` on failure:

```python
from duta import Duta, DutaError

duta = Duta("duta_live_xxx")
try:
    duta.emails.send({ "from": "...", "to": "...", "subject": "Hi", "text": "Hello" })
except DutaError as e:
    print(e.status_code, e.name, e.message)
    # e.name: authentication_error | permission_denied | rate_limit_exceeded | ...
```

## API

### `Duta(api_key, base_url=..., timeout=30.0)`

### `duta.emails.send(params)`

`params` keys: `from`, `to` (str or list), `subject`, `html`, `text`, `reply_to`, `tags` (dict). Returns a dict with `id` and `status`.

### `duta.emails.get(email_id)`

Retrieve one email. Requires a full-access API key.

### `duta.emails.list(page=1, limit=20)`

List emails, newest first. Requires a full-access API key.

## License

MIT
