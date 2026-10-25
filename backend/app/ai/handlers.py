from typing import Any

from .pipeline import AnalysisPipeline, build_link_job


def handle_analyse(
    payload: dict[str, Any],
    pipeline: AnalysisPipeline,
) -> dict[str, Any]:
    """
    Handler called by B's worker for an analyse job.

    Expected payload:
        {
            "evidence_id": "...",
            "text": "..."
        }
    """
    evidence_id = str(payload["evidence_id"])
    text = str(payload["text"])

    return pipeline.analyse(
        evidence_id=evidence_id,
        text=text,
    )


def handle_link(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Handler called by B's worker for a link job.

    Expected payload:
        {
            "case_id": "...",
            "entities": [...],
            "other_cases": [...],
            "rejected_links": [...]
        }
    """
    case_id = str(payload["case_id"])

    entities = payload.get("entities", [])
    other_cases = payload.get("other_cases", [])

    rejected_links = {
        tuple(link)
        for link in payload.get(
            "rejected_links",
            [],
        )
    }

    return build_link_job(
        current_case_id=case_id,
        current_entities=entities,
        other_cases=other_cases,
        rejected_links=rejected_links,
    )


HANDLERS = {
    "analyse": handle_analyse,
    "link": handle_link,
}