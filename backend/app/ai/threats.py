import re

from .schemas import ThreatFlag


THREAT_PATTERNS: dict[str, list[str]] = {
    "violence_threat": [
        r"\bkill\b",
        r"\bshoot\b",
        r"\bhurt you\b",
        r"\battack you\b",
        r"\bbeat you\b",
    ],
    "harassment_stalking": [
        r"\bi am watching you\b",
        r"\bwatching you\b",
        r"\bi know where you live\b",
        r"\bfind you\b",
        r"\bfollowing you\b",
    ],
    "extortion_blackmail": [
        r"\bpay me\b",
        r"\bsend money\b",
        r"\bor i will expose\b",
        r"\bor i will leak\b",
        r"\bblackmail\b",
    ],
    "hate_speech": [
        r"\bgo back to your country\b",
        r"\byour kind\b",
    ],
    "fraud_scam": [
        r"\bsend your otp\b",
        r"\bshare your otp\b",
        r"\bsend your password\b",
        r"\bgive me your password\b",
        r"\bverify your account\b",
    ],
    "self_harm_risk": [
        r"\bi want to die\b",
        r"\bi will kill myself\b",
        r"\bkill myself\b",
        r"\bend my life\b",
    ],
}


def _severity_for(category: str, text: str) -> str:
    """Assign a simple baseline severity."""
    text_lower = text.lower()

    if category == "self_harm_risk":
        return "critical"

    critical_patterns = [
        r"\btonight\b",
        r"\btoday\b",
        r"\bright now\b",
        r"\bat \d{1,2}(:\d{2})?\b",
    ]

    if any(re.search(pattern, text_lower) for pattern in critical_patterns):
        return "critical"

    if category in {
        "violence_threat",
        "extortion_blackmail",
        "fraud_scam",
    }:
        return "high"

    if category in {
        "harassment_stalking",
        "hate_speech",
    }:
        return "medium"

    return "low"


def classify_threats(text: str) -> list[ThreatFlag]:
    """Detect baseline threat patterns in evidence text."""
    flags: list[ThreatFlag] = []

    for category, patterns in THREAT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)

            if not match:
                continue

            snippet = match.group()

            flags.append(
                ThreatFlag(
                    category=category,
                    severity=_severity_for(category, text),
                    confidence=0.75,
                    snippet=snippet,
                )
            )

            break

    return flags


def validate_snippets(
    text: str,
    flags: list[ThreatFlag],
) -> list[ThreatFlag]:
    """Keep only flags whose snippets occur verbatim in the source."""
    return [
        flag
        for flag in flags
        if flag.snippet in text
    ]