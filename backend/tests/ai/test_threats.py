from backend.app.ai.threats import (
    classify_threats,
    validate_snippets,
)


def test_detects_violence_threat():
    text = "I will kill you."

    flags = classify_threats(text)

    assert any(
        flag.category == "violence_threat"
        for flag in flags
    )


def test_detects_self_harm_risk():
    text = "I want to die."

    flags = classify_threats(text)

    assert any(
        flag.category == "self_harm_risk"
        and flag.severity == "critical"
        for flag in flags
    )


def test_detects_fraud_scam():
    text = "Send your OTP to verify your account."

    flags = classify_threats(text)

    assert any(
        flag.category == "fraud_scam"
        for flag in flags
    )


def test_snippet_is_verbatim():
    text = "I will kill you."

    flags = classify_threats(text)

    assert flags

    for flag in flags:
        assert flag.snippet in text


def test_invalid_snippet_is_removed():
    text = "I will kill you."

    flags = classify_threats(text)

    flags[0] = flags[0].model_copy(
        update={"snippet": "This text was invented by the AI."}
    )

    validated = validate_snippets(text, flags)

    assert validated == []


def test_safe_text_has_no_threats():
    text = "The weather is nice today."

    flags = classify_threats(text)

    assert flags == []