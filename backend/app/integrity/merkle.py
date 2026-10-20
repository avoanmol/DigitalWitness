from __future__ import annotations

from hashlib import sha256
from typing import Literal, Sequence, TypedDict


class ProofStep(TypedDict):
    hash: str
    side: Literal["left", "right"]


def _validate_digest(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def leaf_hash(file_sha256_hex: str) -> bytes:
    _validate_digest(file_sha256_hex, "file_sha256_hex")
    return sha256(b"\x00" + bytes.fromhex(file_sha256_hex)).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    if len(left) != 32 or len(right) != 32:
        raise ValueError("Merkle child hashes must each be 32 bytes")
    return sha256(b"\x01" + left + right).digest()


def build_levels(file_hashes: Sequence[str]) -> list[list[bytes]]:
    if not file_hashes:
        raise ValueError("at least one file hash is required")

    level = [leaf_hash(file_hash) for file_hash in file_hashes]
    levels = [level]

    while len(level) > 1:
        next_level = []
        for index in range(0, len(level), 2):
            if index + 1 < len(level):
                next_level.append(node_hash(level[index], level[index + 1]))
            else:
                next_level.append(level[index])
        level = next_level
        levels.append(level)

    return levels


def get_proof(levels: Sequence[Sequence[bytes]], index: int) -> list[ProofStep]:
    if not levels or not levels[0]:
        raise ValueError("levels must contain at least one leaf")
    if index < 0 or index >= len(levels[0]):
        raise IndexError("leaf index is out of range")

    proof: list[ProofStep] = []
    for level in levels[:-1]:
        sibling_index = index ^ 1
        if sibling_index < len(level):
            proof.append(
                {
                    "hash": level[sibling_index].hex(),
                    "side": "left" if sibling_index < index else "right",
                }
            )
        index //= 2

    return proof


def root_from_proof(
    file_sha256_hex: str,
    proof: Sequence[ProofStep],
) -> str:
    _validate_digest(file_sha256_hex, "file_sha256_hex")
    current = leaf_hash(file_sha256_hex)

    for step in proof:
        sibling_hex = step["hash"]
        _validate_digest(sibling_hex, "proof hash")
        sibling = bytes.fromhex(sibling_hex)

        if step["side"] == "left":
            current = node_hash(sibling, current)
        elif step["side"] == "right":
            current = node_hash(current, sibling)
        else:
            raise ValueError("proof side must be 'left' or 'right'")

    return current.hex()


def verify_proof(
    file_sha256_hex: str,
    proof: Sequence[ProofStep],
    root_hex: str,
) -> bool:
    expected_root = root_hex.removeprefix("0x")
    _validate_digest(expected_root, "root_hex")
    return root_from_proof(file_sha256_hex, proof) == expected_root
