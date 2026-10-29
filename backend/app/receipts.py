"""Canonical, HMAC-signed upload receipts."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any


def canonical_receipt_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_receipt(payload: dict[str, Any]) -> str:
    key = os.getenv("RECEIPT_HMAC_KEY")
    if not key or len(key.encode("utf-8")) < 32:
        raise RuntimeError("RECEIPT_HMAC_KEY must contain at least 32 bytes.")
    return hmac.new(key.encode("utf-8"), canonical_receipt_bytes(payload), hashlib.sha256).hexdigest()


def verify_receipt(payload: dict[str, Any], signature: str) -> bool:
    try:
        expected = sign_receipt(payload)
    except RuntimeError:
        return False
    return hmac.compare_digest(expected, signature)


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
