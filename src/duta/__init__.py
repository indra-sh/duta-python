"""Official Python SDK for Duta — transactional email for developers."""

from .client import Duta, Emails
from .errors import DutaError

__all__ = ["Duta", "Emails", "DutaError"]
__version__ = "0.1.0"
