import json
from pathlib import Path
from typing import Any


COMMON_ENTITIES_PATH = (
    Path(__file__).parent / "common_entities.json"
)


BASE_CONFIDENCE = {
    "phone": 0.90,
    "email": 0.90,
    "handle": 0.70,
    "url": 0.60,
}


def load_common_entities() -> dict[str, set[str]]:
    """Load generic entities that should not create case links."""
    if not COMMON_ENTITIES_PATH.exists():
        return {}

    with COMMON_ENTITIES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return {
        entity_type: set(values)
        for entity_type, values in data.items()
    }


def is_common_entity(
    entity_type: str,
    normalised_value: str,
) -> bool:
    """Return True when an entity is on the generic allowlist."""
    common_entities = load_common_entities()

    return normalised_value in common_entities.get(
        entity_type,
        set(),
    )


def calculate_link_confidence(
    shared_entity_types: list[str],
) -> float:
    """
    Calculate link confidence.

    Base confidence comes from the strongest shared entity.
    Each additional shared entity adds 0.05.
    Maximum confidence is 0.99.
    """
    if not shared_entity_types:
        return 0.0

    base = max(
        BASE_CONFIDENCE.get(entity_type, 0.0)
        for entity_type in shared_entity_types
    )

    extra_entities = max(
        0,
        len(shared_entity_types) - 1,
    )

    confidence = base + (0.05 * extra_entities)

    return round(
        min(confidence, 0.99),
        2,
    )

def order_case_pair(
    case_a_id: str,
    case_b_id: str,
) -> tuple[str, str]:
    """Store case pairs in deterministic order."""
    if case_a_id < case_b_id:
        return case_a_id, case_b_id

    return case_b_id, case_a_id


def find_shared_entities(
    current_case_id: str,
    current_entities: list[dict[str, Any]],
    other_cases: list[dict[str, Any]],
    rejected_links: set[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """
    Find suggested links between the current case and other cases.

    Each entity must contain:
        type
        normalised_value

    Each other case must contain:
        case_id
        entities
    """
    rejected_links = rejected_links or set()

    suggestions: list[dict[str, Any]] = []

    current_by_key: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}

    for entity in current_entities:
        entity_type = entity["type"]
        normalised_value = entity["normalised_value"]

        if is_common_entity(
            entity_type,
            normalised_value,
        ):
            continue

        current_by_key[
            (entity_type, normalised_value)
        ] = entity

    for other_case in other_cases:
        other_case_id = str(other_case["case_id"])

        if other_case_id == current_case_id:
            continue

        case_a_id, case_b_id = order_case_pair(
            current_case_id,
            other_case_id,
        )

        if (case_a_id, case_b_id) in rejected_links:
            continue

        shared_entities: list[dict[str, Any]] = []

        for entity in other_case.get("entities", []):
            key = (
                entity["type"],
                entity["normalised_value"],
            )

            if key not in current_by_key:
                continue

            shared_entities.append(
                {
                    "type": entity["type"],
                    "normalised_value": entity[
                        "normalised_value"
                    ],
                }
            )

        if not shared_entities:
            continue

        entity_types = [
            entity["type"]
            for entity in shared_entities
        ]

        confidence = calculate_link_confidence(
            entity_types
        )

        suggestions.append(
            {
                "case_a_id": case_a_id,
                "case_b_id": case_b_id,
                "confidence": confidence,
                "shared_entities": shared_entities,
                "status": "suggested",
            }
        )

    return suggestions