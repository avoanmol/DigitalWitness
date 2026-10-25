import json
from pathlib import Path

from backend.app.ai.extract import extract_entities
from backend.app.ai.threats import classify_threats


EVAL_FILE = Path(__file__).parent / "eval_cases.json"


def load_cases() -> list[dict]:
    with EVAL_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def run_eval() -> dict:
    cases = load_cases()

    results = []

    for case in cases:
        entities = extract_entities(case["text"])
        threats = classify_threats(case["text"])

        actual_entities = sorted(
            {
                entity.type
                for entity in entities
            }
        )

        actual_threats = sorted(
            {
                threat.category
                for threat in threats
            }
        )

        expected_entities = sorted(
            case["expected_entities"]
        )

        expected_threats = sorted(
            case["expected_threats"]
        )

        results.append(
            {
                "id": case["id"],
                "language": case["language"],
                "entities_match": (
                    actual_entities
                    == expected_entities
                ),
                "threats_match": (
                    actual_threats
                    == expected_threats
                ),
                "actual_entities": actual_entities,
                "actual_threats": actual_threats,
            }
        )

    passed = sum(
        result["entities_match"]
        and result["threats_match"]
        for result in results
    )

    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


if __name__ == "__main__":
    report = run_eval()

    print(
        f"Passed: {report['passed']}/"
        f"{report['total']}"
    )

    for result in report["results"]:
        if not (
            result["entities_match"]
            and result["threats_match"]
        ):
            print(
                f"FAIL {result['id']}: "
                f"{result}"
            )