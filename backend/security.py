
import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def get_encryption_key() -> bytes:
    encoded_key = os.getenv("EVIDENCE_ENC_KEY")

    if not encoded_key:
        raise RuntimeError("EVIDENCE_ENC_KEY is not configured.")

    try:
        key = base64.b64decode(encoded_key, validate=True)
    except Exception:
        raise RuntimeError(
            "EVIDENCE_ENC_KEY must be a valid Base64-encoded key."
        ) from None

    if len(key) != 32:
        raise RuntimeError(
            "EVIDENCE_ENC_KEY must decode to exactly 32 bytes."
        )

    return key


def encrypt_evidence(data: bytes) -> tuple[bytes, bytes]:
    """Return (ciphertext, nonce) using AES-256-GCM."""
    if not isinstance(data, bytes):
        raise TypeError("Evidence data must be bytes.")

    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(get_encryption_key())
    ciphertext = aesgcm.encrypt(nonce, data, None)

    return ciphertext, nonce


def decrypt_evidence(ciphertext: bytes, nonce: bytes) -> bytes:
    """Decrypt evidence and authenticate its integrity."""
    aesgcm = AESGCM(get_encryption_key())
    return aesgcm.decrypt(nonce, ciphertext, None)
