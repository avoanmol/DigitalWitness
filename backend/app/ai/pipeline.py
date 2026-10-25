from typing import Any, Callable

from .extract import extract_entities
from .linking import find_shared_entities
from .threats import classify_threats, validate_snippets


class AnalysisPipeline:
    """
    Runs the AI analysis pipeline.

    Database writes are injected through callbacks so this module
    does not depend on B's SQLAlchemy models.
    """

    def __init__(
        self,
        save_entities: Callable[
            [str, list[dict[str, Any]]],
            None,
        ],
        save_flags: Callable[
            [str, list[dict[str, Any]]],
            None,
        ],
        update_status: Callable[[str, str], None],
    ) -> None:
        self.save_entities = save_entities
        self.save_flags = save_flags
        self.update_status = update_status

    def analyse(
        self,
        evidence_id: str,
        text: str,
    ) -> dict[str, Any]:
        """
        Analyse one evidence item.

        Re-running this method replaces the generated result through
        the injected persistence functions instead of creating a
        second in-memory result.
        """
        self.update_status(
            evidence_id,
            "processing",
        )

        try:
            entities = extract_entities(text)

            flags = classify_threats(text)
            flags = validate_snippets(
                text,
                flags,
            )

            entity_data = [
                {
                    "type": entity.type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "snippet": entity.snippet,
                }
                for entity in entities
            ]

            flag_data = [
                {
                    "category": flag.category,
                    "severity": flag.severity,
                    "confidence": flag.confidence,
                    "snippet": flag.snippet,
                }
                for flag in flags
            ]

            self.save_entities(
                evidence_id,
                entity_data,
            )

            self.save_flags(
                evidence_id,
                flag_data,
            )

            self.update_status(
                evidence_id,
                "done",
            )

            return {
                "evidence_id": evidence_id,
                "status": "done",
                "entities": entity_data,
                "flags": flag_data,
            }

        except Exception:
            self.update_status(
                evidence_id,
                "failed",
            )

            return {
                "evidence_id": evidence_id,
                "status": "failed",
                "entities": [],
                "flags": [],
            }


def build_link_job(
    current_case_id: str,
    current_entities: list[dict[str, Any]],
    other_cases: list[dict[str, Any]],
    rejected_links: set[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Generate link suggestions for one analysed case."""
    return find_shared_entities(
        current_case_id=current_case_id,
        current_entities=current_entities,
        other_cases=other_cases,
        rejected_links=rejected_links,
    )