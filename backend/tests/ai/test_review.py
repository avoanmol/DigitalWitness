from backend.app.ai.review import add_review_metadata


def test_results_require_human_review():
    result = {
        "evidence_id": "ev-001",
        "status": "done",
        "entities": [
            {
                "type": "email",
                "value": "test@example.com",
                "confidence": 1.0,
                "snippet": "test@example.com",
            }
        ],
        "flags": [
            {
                "category": "violence_threat",
                "severity": "high",
                "confidence": 0.75,
                "snippet": "kill you",
            }
        ],
    }

    reviewed = add_review_metadata(result)

    assert reviewed["human_review_required"] is True
    assert reviewed["entities"][0]["review_status"] == "pending"
    assert reviewed["flags"][0]["review_status"] == "pending"


def test_empty_result_still_requires_review():
    result = {
        "evidence_id": "ev-002",
        "status": "done",
        "entities": [],
        "flags": [],
    }

    reviewed = add_review_metadata(result)

    assert reviewed["human_review_required"] is True
    assert reviewed["entities"] == []
    assert reviewed["flags"] == []