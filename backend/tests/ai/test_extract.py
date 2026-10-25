from backend.app.ai.extract import extract_entities


def test_extracts_email():
    text = "Contact test@example.com for more information."

    entities = extract_entities(text)

    assert any(
        entity.type == "email"
        and entity.value == "test@example.com"
        for entity in entities
    )


def test_extracts_phone():
    text = "Call +91 9876543210."

    entities = extract_entities(text)

    assert any(
        entity.type == "phone"
        and entity.value == "+91 9876543210"
        for entity in entities
    )


def test_extracts_url():
    text = "Visit https://example.com/case/123."

    entities = extract_entities(text)

    assert any(
        entity.type == "url"
        and entity.value == "https://example.com/case/123"
        for entity in entities
    )


def test_extracts_handle():
    text = "Telegram: @rahul123"

    entities = extract_entities(text)

    assert any(
        entity.type == "handle"
        and entity.value == "@rahul123"
        for entity in entities
    )