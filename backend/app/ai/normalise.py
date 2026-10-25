import re
import unicodedata


def normalize_text(value: str) -> str:
    """Normalize Unicode text and surrounding whitespace."""
    value = unicodedata.normalize("NFKC", value)
    return value.strip()


def normalize_phone(value: str) -> str:
    """Normalize an Indian phone number into digits with country code."""
    value = normalize_text(value)

    digits = re.sub(r"\D", "", value)

    if len(digits) == 10:
        return f"+91{digits}"

    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"

    return value


def normalize_email(value: str) -> str:
    """Normalize an email address for comparison."""
    return normalize_text(value).lower()


def normalize_handle(value: str) -> str:
    """Normalize a username/handle for comparison."""
    value = normalize_text(value)

    if not value.startswith("@"):
        value = f"@{value}"

    return value.lower()


def normalize_url(value: str) -> str:
    """Normalize a URL for basic comparison."""
    return normalize_text(value).rstrip("/")