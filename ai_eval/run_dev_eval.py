"""Evaluate only synthetic development examples; never reads challenge or private data."""
import json
from collections import defaultdict
from pathlib import Path
from backend.app.ai.threats import detect_threats

ROOT = Path(__file__).resolve().parent


def metrics(expected, predicted):
    tp = sum(a and b for a, b in zip(expected, predicted))
    fp = sum((not a) and b for a, b in zip(expected, predicted))
    fn = sum(a and (not b) for a, b in zip(expected, predicted))
    tn = sum((not a) and (not b) for a, b in zip(expected, predicted))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"cases": len(expected), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1}


def main():
    baseline = [json.loads(line) for line in (ROOT / "samples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    stress = [json.loads(line) for line in (ROOT / "development_scenarios.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    fictional = [json.loads(line) for line in (ROOT / "fictional_scenario_set.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for row in baseline:
        predictions = detect_threats(row["text"], row["language"])
        results.append({"id": row["id"], "split": "baseline", "language": row["language"],
                        "scenario": row.get("scenario", "unspecified"),
                        "expected_threat": bool(row["expected_threat"]), "predicted_threat": bool(predictions),
                        "expected_category": None, "predicted_categories": sorted({item.threat_class for item in predictions})})
    for row in stress:
        predictions = detect_threats(row["text"], row["language"])
        results.append({"id": row["id"], "split": "scenario_stress", "language": row["language"],
                        "scenario": row["scenario"], "expected_threat": bool(row["expected_threat"]),
                        "predicted_threat": bool(predictions), "expected_category": row["expected_category"],
                        "predicted_categories": sorted({item.threat_class for item in predictions})})
    fictional_results = []
    for row in fictional:
        predictions = detect_threats(row["text"], row["language"])
        fictional_results.append({"id": row["id"], "scenario": row["scenario"],
                                  "expected_threat": bool(row["expected_threat"]),
                                  "predicted_threat": bool(predictions),
                                  "expected_category": row["expected_category"],
                                  "predicted_categories": sorted({item.threat_class for item in predictions})})
    by_language = {}
    for language in sorted({item["language"] for item in results}):
        group = [item for item in results if item["language"] == language]
        by_language[language] = metrics([r["expected_threat"] for r in group], [r["predicted_threat"] for r in group])
    by_scenario = {}
    for scenario in sorted({item["scenario"] for item in results if item["split"] == "scenario_stress"}):
        group = [item for item in results if item["scenario"] == scenario]
        category_hits = sum(r["expected_category"] in r["predicted_categories"] for r in group if r["expected_threat"])
        positive_count = sum(r["expected_threat"] for r in group)
        by_scenario[scenario] = {**metrics([r["expected_threat"] for r in group], [r["predicted_threat"] for r in group]),
                                 "expected_category_hits": category_hits, "positive_cases": positive_count}
    report = {
        "scope": "Synthetic development examples only. Does not read private cases or the held-out challenge set.",
        "baseline_case_count": len(baseline), "scenario_stress_case_count": len(stress),
        "overall": metrics([r["expected_threat"] for r in results], [r["predicted_threat"] for r in results]),
        "by_language": by_language, "by_scenario": by_scenario,
        "mismatches": [r for r in results if r["expected_threat"] != r["predicted_threat"] or
                       (r["expected_threat"] and r["expected_category"] is not None
                        and r["expected_category"] not in r["predicted_categories"])],
        "fictional_scenario_set": {
            "scope": "200 author-written English scenarios; labels are not independently reviewed and are not real-world accuracy evidence.",
            "case_count": len(fictional_results),
            "by_scenario": {
                scenario: {
                    **metrics(
                        [row["expected_threat"] for row in fictional_results if row["scenario"] == scenario],
                        [row["predicted_threat"] for row in fictional_results if row["scenario"] == scenario],
                    ),
                    "expected_category_hits": sum(
                        row["expected_category"] in row["predicted_categories"]
                        for row in fictional_results
                        if row["scenario"] == scenario and row["expected_threat"]
                    ),
                    "positive_cases": sum(
                        row["expected_threat"]
                        for row in fictional_results
                        if row["scenario"] == scenario
                    ),
                }
                for scenario in sorted({row["scenario"] for row in fictional_results})
            },
            "mismatches": [
                row for row in fictional_results
                if row["expected_threat"] != row["predicted_threat"] or
                (row["expected_threat"] and row["expected_category"] not in row["predicted_categories"])
            ],
        },
    }
    (ROOT / "development_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"baseline_case_count": len(baseline), "scenario_stress_case_count": len(stress),
                      "overall": report["overall"], "by_scenario": by_scenario,
                      "mismatch_count": len(report["mismatches"]),
                      "fictional_case_count": len(fictional_results),
                      "fictional_by_scenario": report["fictional_scenario_set"]["by_scenario"],
                      "fictional_mismatch_count": len(report["fictional_scenario_set"]["mismatches"]),
                      "report_path": "ai_eval/development_report.json"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
