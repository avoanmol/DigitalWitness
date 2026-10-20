from backend.app.ai.job_keys import (
    analysis_job_key,
    link_job_key,
)


def test_analysis_job_key_is_deterministic():
    first = analysis_job_key(
        "ev-001",
        "abc123",
    )

    second = analysis_job_key(
        "ev-001",
        "abc123",
    )

    assert first == second


def test_different_hash_creates_different_key():
    first = analysis_job_key(
        "ev-001",
        "abc123",
    )

    second = analysis_job_key(
        "ev-001",
        "different",
    )

    assert first != second


def test_link_job_key_is_deterministic():
    assert link_job_key("case-001") == link_job_key(
        "case-001"
    )


def test_different_cases_have_different_keys():
    assert link_job_key("case-001") != link_job_key(
        "case-002"
    )