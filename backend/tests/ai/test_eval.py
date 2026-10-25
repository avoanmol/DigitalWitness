from pathlib import Path

from ai_eval.run_eval import load_cases


def test_eval_set_exists():
    path = Path("ai_eval/eval_cases.json")

    assert path.exists()


def test_eval_set_has_cases():
    cases = load_cases()

    assert len(cases) >= 10


def test_eval_cases_have_required_fields():
    cases = load_cases()

    for case in cases:
        assert "id" in case
        assert "language" in case
        assert "text" in case
        assert "expected_entities" in case
        assert "expected_threats" in case


def test_eval_contains_indian_languages():
    cases = load_cases()

    languages = {
        case["language"]
        for case in cases
    }

    assert "hi" in languages
    assert "kn" in languages