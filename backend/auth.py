
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash

# Read these values from environment variables.
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET must be configured with a strong secret "
        "of at least 32 characters."
    )

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a secure hash of a password."""
    if not password:
        raise ValueError("Password cannot be empty.")
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against its stored hash."""
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: UUID, role: str) -> str:
    """Create a signed JWT with subject, role, issued-at, and expiration."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Validate a JWT and return its claims."""
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp"]},
    )

    # Reject malformed user identifiers.
    UUID(payload["sub"])
    return payload
