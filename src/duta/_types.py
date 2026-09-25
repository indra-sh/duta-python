"""Request shapes, from Duta's OpenAPI spec (https://api.duta.indra.sh/openapi.json).

Plain dicts work everywhere; these types are for editors and type checkers.
"""

from __future__ import annotations

from typing import Dict, List, Literal, TypedDict, Union


class AddressParams(TypedDict, total=False):
    email: str
    name: str


Address = Union[str, AddressParams]
"""``"Name <email>"``, a plain address, or ``{"email": ..., "name": ...}``."""


class AttachmentParams(TypedDict, total=False):
    filename: str
    content: str  # base64
    path: str  # a public https URL Duta downloads; not accepted in a batch
    content_type: str
    content_id: str


class TagParams(TypedDict):
    name: str
    value: str


# Functional form, because "from" is a Python keyword.
SendEmailParams = TypedDict(
    "SendEmailParams",
    {
        "from": Address,
        "to": Union[Address, List[Address]],
        "subject": str,
        "html": str,
        "text": str,
        "cc": Union[Address, List[Address]],
        "bcc": Union[Address, List[Address]],
        "reply_to": Union[Address, List[Address]],
        "headers": Dict[str, str],
        "attachments": List[AttachmentParams],
        "tags": Union[List[TagParams], Dict[str, str]],
    },
    total=False,
)


class DomainParams(TypedDict):
    name: str


class ApiKeyParams(TypedDict, total=False):
    name: str
    permission: Literal["full_access", "sending_access"]


class WebhookParams(TypedDict, total=False):
    endpoint: str
    events: List[str]


class PageQuery(TypedDict, total=False):
    limit: int
    after: str


class EmailListQuery(PageQuery, total=False):
    q: str
    status: str


class LogListQuery(PageQuery, total=False):
    q: str
    status: str
    method: str


class SuppressionListQuery(PageQuery, total=False):
    q: str
