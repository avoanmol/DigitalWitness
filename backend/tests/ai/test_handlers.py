from backend.app.ai.handlers import (
    HANDLERS,
    handle_analyse,
    handle_link,
)
from backend.app.ai.pipeline import AnalysisPipeline


def test_handlers_are_registered():
    assert "analyse" in HANDLERS
    assert "link" in HANDLERS


def test_analyse_handler():
    statuses = []

    def save_entities(evidence_id, entities):
        pass

    def save_flags(evidence_id, flags):
        pass

    def update_status(evidence_id, status):
        statuses.append(status)

    pipeline = AnalysisPipeline(
        save_entities=save_entities,
        save_flags=save_flags,
        update_status=update_status,
    )

    result = handle_analyse(
        {
            "evidence_id": "ev-001",
            "text": "Contact test@example.com",
        },
        pipeline,
    )

    assert result["status"] == "done"
    assert result["evidence_id"] == "ev-001"
    assert statuses == ["processing", "done"]


def test_link_handler():
    result = handle_link(
        {
            "case_id": "case-001",
            "entities": [
                {
                    "type": "phone",
                    "normalised_value": "+919876543210",
                }
            ],
            "other_cases": [
                {
                    "case_id": "case-002",
                    "entities": [
                        {
                            "type": "phone",
                            "normalised_value": "+919876543210",
                        }
                    ],
                }
            ],
        }
    )

    assert len(result) == 1
    assert result[0]["case_a_id"] == "case-001"
    assert result[0]["case_b_id"] == "case-002"
    assert result[0]["confidence"] == 0.90


def test_link_handler_respects_rejected_links():
    result = handle_link(
        {
            "case_id": "case-001",
            "entities": [
                {
                    "type": "phone",
                    "normalised_value": "+919876543210",
                }
            ],
            "other_cases": [
                {
                    "case_id": "case-002",
                    "entities": [
                        {
                            "type": "phone",
                            "normalised_value": "+919876543210",
                        }
                    ],
                }
            ],
            "rejected_links": [
                ["case-001", "case-002"],
            ],
        }
    )

    assert result == []