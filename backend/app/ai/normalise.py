from __future__ import annotations
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import phonenumbers

def _load_common_domains() -> set[str]:
    path = Path(__file__).with_name("common_entities.json")
    try:
        return {str(item).lower() for item in json.loads(path.read_text(encoding="utf-8"))["common_url_domains"]}
    except (OSError, ValueError, KeyError, TypeError):
        return set()

COMMON_URL_DOMAINS = _load_common_domains()

def _ascii_digits(value: str) -> str:
    return "".join(str(unicodedata.digit(char)) if char.isdigit() else char for char in value)

def normalise_phone(value: str, default_region: str = "IN") -> str | None:
    cleaned = _ascii_digits(value).strip()
    try:
        parsed = phonenumbers.parse(cleaned, None if cleaned.startswith("+") else default_region)
        if phonenumbers.is_possible_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    digits = re.sub(r"\D", "", cleaned)
    if not 7 <= len(digits) <= 15:
        return None
    if cleaned.startswith("+"):
        return "+" + digits
    return "+91" + digits if len(digits) == 10 else "+" + digits

def normalise_url(value: str) -> str | None:
    value = value.strip()
    while value and value[-1] in ".,;:!?)]}":
        value = value[:-1]
    candidate = value if "://" in value else "https://" + value
    try:
        parts = urlsplit(candidate)
        host = (parts.hostname or "").lower().rstrip(".")
        if not host or parts.username or parts.password:
            return None
        if host.startswith("www."):
            host = host[4:]
        port = parts.port
        netloc = host if port is None or port in {80, 443} else f"{host}:{port}"
        return urlunsplit(("", netloc, parts.path.rstrip("/"), "", ""))
    except ValueError:
        return None

def is_common_url(value: str) -> bool:
    normalized = normalise_url(value)
    if not normalized:
        return False
    host = normalized.split("/", 1)[0].split(":", 1)[0]
    return any(host == domain or host.endswith("." + domain) for domain in COMMON_URL_DOMAINS)

def normalise_entity(entity_type: str, value: str) -> str | None:
    raw = unicodedata.normalize("NFKC", value).strip()
    if entity_type == "email":
        candidate = raw.removeprefix("mailto:").strip().strip("<>,;").casefold()
        return candidate if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", candidate) else None
    if entity_type == "phone":
        return normalise_phone(raw)
    if entity_type == "handle":
        candidate = raw.lstrip("@").strip().casefold()
        return candidate if re.fullmatch(r"[\w.]{2,64}", candidate, flags=re.UNICODE) else None
    if entity_type == "url":
        return normalise_url(raw)
    return None
