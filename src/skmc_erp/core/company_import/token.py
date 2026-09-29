import base64
import hashlib
import hmac
import json
import time
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


TOKEN_VERSION = 2
TOKEN_LIFETIME_SECONDS = 15 * 60


class PreviewTokenError(Exception):
    """The preview token is invalid or expired."""


@dataclass(frozen=True)
class PreviewTokenPayload:
    tenant_id: str
    company_id: str
    values: dict[str, Any]
    company_fingerprint: str
    expires_at: datetime


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, UnicodeError) as exc:
        raise PreviewTokenError("Preview token is invalid") from exc


def create_preview_token(
    *,
    signing_key: str,
    tenant_id: str,
    company_id: str,
    values: dict[str, Any],
    company_fingerprint: str,
    now: int | None = None,
) -> tuple[str, datetime]:
    issued_at = int(time.time()) if now is None else now
    expires_at = issued_at + TOKEN_LIFETIME_SECONDS
    payload = {
        "v": TOKEN_VERSION,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "values": values,
        "company_fingerprint": company_fingerprint,
        "iat": issued_at,
        "exp": expires_at,
    }
    encoded_payload = _encode(
        zlib.compress(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
    )
    signature = _encode(
        hmac.new(
            signing_key.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
    )
    return (
        f"{encoded_payload}.{signature}",
        datetime.fromtimestamp(expires_at, tz=UTC),
    )


def read_preview_token(
    token: str,
    *,
    signing_key: str,
    now: int | None = None,
) -> PreviewTokenPayload:
    try:
        encoded_payload, supplied_signature = token.split(".", maxsplit=1)
    except ValueError as exc:
        raise PreviewTokenError("Preview token is invalid") from exc

    expected_signature = _encode(
        hmac.new(
            signing_key.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
    )
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise PreviewTokenError("Preview token is invalid")

    try:
        raw = json.loads(zlib.decompress(_decode(encoded_payload)))
        if raw["v"] != TOKEN_VERSION:
            raise PreviewTokenError("Preview token version is not supported")
        current_time = int(time.time()) if now is None else now
        if not isinstance(raw["exp"], int) or raw["exp"] <= current_time:
            raise PreviewTokenError("Preview token has expired")
        if not isinstance(raw["values"], dict):
            raise PreviewTokenError("Preview token is invalid")
        return PreviewTokenPayload(
            tenant_id=str(raw["tenant_id"]),
            company_id=str(raw["company_id"]),
            values=raw["values"],
            company_fingerprint=str(raw["company_fingerprint"]),
            expires_at=datetime.fromtimestamp(raw["exp"], tz=UTC),
        )
    except (KeyError, TypeError, ValueError, zlib.error) as exc:
        raise PreviewTokenError("Preview token is invalid") from exc
