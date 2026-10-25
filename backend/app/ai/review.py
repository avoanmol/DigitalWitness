from typing import Any


def add_review_metadata(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Mark AI results as requiring human review.

    AI output is never automatically treated as confirmed.
    """
    reviewed_result = dict(result)

    reviewed_result["human_review_required"] = True

    reviewed_result["entities"] = [
        {
            **entity,
            "review_status": "pending",
        }
        for entity in result.get("entities", [])
    ]

    reviewed_result["flags"] = [
        {
            **flag,
            "review_status": "pending",
        }
        for flag in result.get("flags", [])
    ]

    return reviewed_result