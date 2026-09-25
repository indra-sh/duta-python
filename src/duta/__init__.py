"""The official Python SDK for Duta, transactional email for Malaysia.

https://docs.duta.indra.sh
"""

from ._client import AsyncDuta, Duta
from ._errors import DutaError, WebhookVerificationError
from ._types import AddressParams, AttachmentParams, SendEmailParams
from ._version import __version__
from ._webhooks import verify as verify_webhook

__all__ = [
    "Duta",
    "AsyncDuta",
    "DutaError",
    "WebhookVerificationError",
    "verify_webhook",
    "SendEmailParams",
    "AddressParams",
    "AttachmentParams",
    "__version__",
]
