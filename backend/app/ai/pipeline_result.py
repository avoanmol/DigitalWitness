from typing import Any


def success_result(
    evidence_id: str,
    entities: list[dict[str, Any]],
    flags: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "status": "done",
        "entities": entities,
        "flags": flags,
    }


def failed_result(
    evidence_id: str,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "status": "failed",
        "entities": [],
        "flags": [],
    }


def skipped_result(
    evidence_id: str,
    reason: str = "already_processed",
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "status": "skipped",
        "reason": reason,
        "entities": [],
        "flags": [],
    }