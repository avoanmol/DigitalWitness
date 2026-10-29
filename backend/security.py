
import base64
import os
import secrets
from typing import BinaryIO

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


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


def encrypt_evidence_stream(source: BinaryIO, destination: BinaryIO) -> bytes:
    """Encrypt a seekable evidence stream without holding the whole file in RAM.

    The stored representation remains ``nonce || ciphertext || tag``, matching
    :func:`decrypt_evidence` and existing evidence objects.
    """
    nonce = secrets.token_bytes(12)
    encryptor = Cipher(algorithms.AES(get_encryption_key()), modes.GCM(nonce)).encryptor()
    destination.write(nonce)
    source.seek(0)
    while True:
        chunk = source.read(1024 * 1024)
        if not chunk:
            break
        destination.write(encryptor.update(chunk))
    destination.write(encryptor.finalize())
    destination.write(encryptor.tag)
    destination.seek(0)
    return nonce


def decrypt_evidence(ciphertext: bytes, nonce: bytes) -> bytes:
    """Decrypt evidence and authenticate its integrity."""
    aesgcm = AESGCM(get_encryption_key())
    return aesgcm.decrypt(nonce, ciphertext, None)


def encrypt_case_secret(value: str, case_id: str) -> tuple[bytes, bytes]:
    """Encrypt a short case-scoped secret and bind it to that case as GCM AAD."""
    if not isinstance(value, str) or not value:
        raise ValueError("A non-empty secret is required.")
    nonce = secrets.token_bytes(12)
    aad = f"digitalwitness:case-secret:v1:{case_id}".encode("utf-8")
    ciphertext = AESGCM(get_encryption_key()).encrypt(nonce, value.encode("utf-8"), aad)
    return ciphertext, nonce


def decrypt_case_secret(ciphertext: bytes, nonce: bytes, case_id: str) -> str:
    """Decrypt a short case-scoped secret after authenticating its case binding."""
    aad = f"digitalwitness:case-secret:v1:{case_id}".encode("utf-8")
    value = AESGCM(get_encryption_key()).decrypt(nonce, ciphertext, aad)
    return value.decode("utf-8")
