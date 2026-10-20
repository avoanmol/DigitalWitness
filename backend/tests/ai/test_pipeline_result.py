from backend.app.ai.pipeline_result import (
    failed_result,
    skipped_result,
    success_result,
)


def test_success_result():
    result = success_result(
        evidence_id="ev-001",
        entities=[
            {
                "type": "email",
                "value": "test@example.com",
            }
        ],
        flags=[],
    )

    assert result["evidence_id"] == "ev-001"
    assert result["status"] == "done"
    assert len(result["entities"]) == 1


def test_failed_result():
    result = failed_result("ev-001")

    assert result["evidence_id"] == "ev-001"
    assert result["status"] == "failed"
    assert result["entities"] == []
    assert result["flags"] == []


def test_skipped_result():
    result = skipped_result("ev-001")

    assert result["evidence_id"] == "ev-001"
    assert result["status"] == "skipped"
    assert result["reason"] == "already_processed"