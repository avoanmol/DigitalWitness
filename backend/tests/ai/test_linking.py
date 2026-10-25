from backend.app.ai.linking import (
    calculate_link_confidence,
    find_shared_entities,
    order_case_pair,
)


def test_phone_confidence():
    confidence = calculate_link_confidence(
        ["phone"]
    )

    assert confidence == 0.90


def test_email_confidence():
    confidence = calculate_link_confidence(
        ["email"]
    )

    assert confidence == 0.90


def test_handle_confidence():
    confidence = calculate_link_confidence(
        ["handle"]
    )

    assert confidence == 0.70


def test_url_confidence():
    confidence = calculate_link_confidence(
        ["url"]
    )

    assert confidence == 0.60


def test_extra_shared_entity_adds_confidence():
    confidence = calculate_link_confidence(
        ["phone", "email"]
    )

    assert confidence == 0.95


def test_confidence_is_capped():
    confidence = calculate_link_confidence(
        ["phone", "email", "handle", "url"]
    )

    assert confidence == 0.99


def test_case_pair_is_ordered():
    assert order_case_pair(
        "case-b",
        "case-a",
    ) == ("case-a", "case-b")


def test_same_phone_creates_link():
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

    suggestions = find_shared_entities(
        current_case_id="case-001",
        current_entities=current_entities,
        other_cases=other_cases,
    )

    assert len(suggestions) == 1
    assert suggestions[0]["case_a_id"] == "case-001"
    assert suggestions[0]["case_b_id"] == "case-002"
    assert suggestions[0]["confidence"] == 0.90
    assert suggestions[0]["status"] == "suggested"


def test_multiple_shared_entities_increase_confidence():
    current_entities = [
        {
            "type": "phone",
            "normalised_value": "+919876543210",
        },
        {
            "type": "email",
            "normalised_value": "test@example.com",
        },
    ]

    other_cases = [
        {
            "case_id": "case-002",
            "entities": [
                {
                    "type": "phone",
                    "normalised_value": "+919876543210",
                },
                {
                    "type": "email",
                    "normalised_value": "test@example.com",
                },
            ],
        }
    ]

    suggestions = find_shared_entities(
        current_case_id="case-001",
        current_entities=current_entities,
        other_cases=other_cases,
    )

    assert len(suggestions) == 1
    assert suggestions[0]["confidence"] == 0.95
    assert len(
        suggestions[0]["shared_entities"]
    ) == 2


def test_does_not_link_case_to_itself():
    current_entities = [
        {
            "type": "phone",
            "normalised_value": "+919876543210",
        }
    ]

    other_cases = [
        {
            "case_id": "case-001",
            "entities": [
                {
                    "type": "phone",
                    "normalised_value": "+919876543210",
                }
            ],
        }
    ]

    suggestions = find_shared_entities(
        current_case_id="case-001",
        current_entities=current_entities,
        other_cases=other_cases,
    )

    assert suggestions == []


def test_rejected_link_is_not_resuggested():
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

    rejected_links = {
        ("case-001", "case-002")
    }

    suggestions = find_shared_entities(
        current_case_id="case-001",
        current_entities=current_entities,
        other_cases=other_cases,
        rejected_links=rejected_links,
    )

    assert suggestions == []


def test_common_url_does_not_create_link():
    current_entities = [
        {
            "type": "url",
            "normalised_value": "https://youtube.com",
        }
    ]

    other_cases = [
        {
            "case_id": "case-002",
            "entities": [
                {
                    "type": "url",
                    "normalised_value": "https://youtube.com",
                }
            ],
        }
    ]

    suggestions = find_shared_entities(
        current_case_id="case-001",
        current_entities=current_entities,
        other_cases=other_cases,
    )

    assert suggestions == []