"""Small single-process login throttle until shared rate limiting is configured."""

from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from math import ceil

MAX_LOGIN_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 15 * 60

_attempts: dict[str, deque[float]] = {}
_attempts_lock = threading.Lock()


def consume_login_attempt(
    email: str,
    ip_address: str,
    *,
    now: float | None = None,
) -> int | None:
    """Record an attempt, or return seconds until IP/email limits expire.

    Email addresses are hashed before being used as in-memory keys. This
    process-local throttle is suitable for the current single-worker setup;
    multi-worker deployments need a shared limiter such as Redis.
    """
    current = time.monotonic() if now is None else now
    email_key = "email:" + hashlib.sha256(email.strip().lower().encode()).hexdigest()
    keys = ("ip:" + (ip_address or "unknown"), email_key)

    with _attempts_lock:
        # Expire old keys too, so random addresses cannot grow this cache forever.
        for key, bucket in list(_attempts.items()):
            while bucket and current - bucket[0] >= LOGIN_WINDOW_SECONDS:
                bucket.popleft()
            if not bucket:
                del _attempts[key]

        retry_after = 0
        for key in keys:
            bucket = _attempts.get(key)
            if bucket and len(bucket) >= MAX_LOGIN_ATTEMPTS:
                retry_after = max(
                    retry_after,
                    ceil(bucket[0] + LOGIN_WINDOW_SECONDS - current),
                )

        if retry_after:
            return retry_after

        for key in keys:
            _attempts.setdefault(key, deque()).append(current)
    return None


def clear_email_attempts(email: str) -> None:
    """Clear the email bucket after successful authentication."""
    email_key = "email:" + hashlib.sha256(email.strip().lower().encode()).hexdigest()
    with _attempts_lock:
        _attempts.pop(email_key, None)


def _reset_attempts_for_tests() -> None:
    """Clear process-local state for isolated unit tests."""
    with _attempts_lock:
        _attempts.clear()
