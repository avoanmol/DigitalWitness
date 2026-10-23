from backend.app.ai.pipeline import (
    AnalysisPipeline,
    build_link_job,
)


def test_analysis_pipeline_saves_entities_and_flags():
    saved_entities = []
    saved_flags = []
    statuses = []

    def save_entities(evidence_id, entities):
        saved_entities.append(
            (evidence_id, entities)
        )

    def save_flags(evidence_id, flags):
        saved_flags.append(
            (evidence_id, flags)
        )

    def update_status(evidence_id, status):
        statuses.append(
            (evidence_id, status)
        )

    pipeline = AnalysisPipeline(
        save_entities=save_entities,
        save_flags=save_flags,
        update_status=update_status,
    )

    result = pipeline.analyse(
        evidence_id="evidence-001",
        text=(
            "Contact me at "
            "test@example.com. "
            "I will kill you."
        ),
    )

    assert result["status"] == "done"

    assert saved_entities[0][0] == "evidence-001"
    assert saved_flags[0][0] == "evidence-001"

    assert ("evidence-001", "processing") in statuses
    assert ("evidence-001", "done") in statuses


def test_analysis_failure_does_not_raise():
    statuses = []

    def failing_save_entities(evidence_id, entities):
        raise RuntimeError("database unavailable")

    def save_flags(evidence_id, flags):
        pass

    def update_status(evidence_id, status):
        statuses.append(
            (evidence_id, status)
        )

    pipeline = AnalysisPipeline(
        save_entities=failing_save_entities,
        save_flags=save_flags,
        update_status=update_status,
    )

    result = pipeline.analyse(
        evidence_id="evidence-001",
        text="safe text",
    )

    assert result["status"] == "failed"
    assert ("evidence-001", "failed") in statuses


def test_link_job_creates_suggestion():
    current_entities = [
        {
            "type": "phone",
            "normalised_value": "+919876543210",
        }
    ]

    other_cases = [
        {
            "case_id": "case-002",
            "entities": [
                {
                    "type": "phone",
                    "normalised_value": "+919876543210",
                }
            ],
        }
    ]

    result = build_link_job(
        current_case_id="case-001",
        current_entities=current_entities,
        other_cases=other_cases,
    )

    assert len(result) == 1
    assert result[0]["confidence"] == 0.90
    assert result[0]["status"] == "suggested"


def test_link_job_does_not_create_self_link():
    entities = [
        {
            "type": "phone",
            "normalised_value": "+919876543210",
        }
    ]

    result = build_link_job(
        current_case_id="case-001",
        current_entities=entities,
        other_cases=[
            {
                "case_id": "case-001",
                "entities": entities,
            }
        ],
    )

    assert result == []