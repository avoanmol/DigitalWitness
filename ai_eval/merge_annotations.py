"""Merge two blind reviewer sheets into the private evaluator's JSONL format."""
import argparse
import csv
import json
from pathlib import Path

SCENARIOS = {"harassment_stalking", "extortion_blackmail", "intimate_image_abuse",
             "fake_profile_impersonation", "defamation_morphing", "other"}
LANGUAGES = {"en", "hi", "kn"}
THREAT_CATEGORIES = {"cyberstalking_bullying", "blackmail_threatening", "intimate_image_abuse",
                     "defamation_morphing", "fake_profile_impersonation", "other"}


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    for row in rows:
        case_id = (row.get("case_id") or "").strip()
        if not case_id or case_id in result:
            raise ValueError("Each annotation sheet needs unique, non-empty case IDs.")
        result[case_id] = row
    return result


def parse_bool(value, case_id, source):
    normalized = (value or "").strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"A threat/no-threat label is missing or invalid in {source} for case {case_id}.")
    return normalized == "true"


def parse_categories(value, case_id, source):
    if value is None:
        raise ValueError(f"Category labels are missing in {source} for case {case_id}.")
    categories = [item.strip().lower() for item in value.split(";") if item.strip()]
    if any(item not in THREAT_CATEGORIES for item in categories) or len(set(categories)) != len(categories):
        raise ValueError(f"Category labels are invalid or duplicated in {source} for case {case_id}.")
    return sorted(categories)


def parse_annotation(row, case_id, source):
    scenario = (row.get("scenario") or "").strip()
    language = (row.get("language") or "").strip().lower()
    if scenario not in SCENARIOS or language not in LANGUAGES:
        raise ValueError(f"Scenario or language is missing or invalid in {source} for case {case_id}.")
    reviewer = (row.get("reviewer_id") or "").strip()
    if not reviewer:
        raise ValueError(f"Reviewer ID is missing in {source} for case {case_id}.")
    expected_threat = parse_bool(row.get("expected_threat"), case_id, source)
    expected_categories = parse_categories(row.get("expected_categories"), case_id, source)
    if expected_threat != bool(expected_categories):
        raise ValueError(f"Threat/no-threat and category labels disagree in {source} for case {case_id}; use an empty category list for no threat and 'other' when threat is present but uncategorised.")
    return {"reviewer_id": reviewer, "scenario": scenario, "language": language,
            "expected_threat": expected_threat, "expected_categories": expected_categories}


def validate_source(row):
    case_id = str(row.get("id", ""))
    source_type = row.get("source_type")
    if source_type == "consented_redacted":
        if not str(row.get("consent_reference", "")).strip():
            raise ValueError(f"Source {case_id} lacks a non-identifying consent reference.")
    elif source_type == "licensed_public":
        if not all(str(row.get(key, "")).strip() for key in ("source_reference", "license")):
            raise ValueError(f"Source {case_id} lacks its source reference or license.")
    else:
        raise ValueError(f"Source {case_id} must be consented_redacted or licensed_public.")
    if not (isinstance(row.get("text"), str) and row["text"].strip()) and not (isinstance(row.get("file"), str) and row["file"].strip()):
        raise ValueError(f"Source {case_id} must have reviewed text or a local evidence file path.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=Path("ai_eval/private_sources.jsonl"))
    parser.add_argument("--reviewer-a", type=Path, default=Path("ai_eval/reviewer_a.csv"))
    parser.add_argument("--reviewer-b", type=Path, default=Path("ai_eval/reviewer_b.csv"))
    parser.add_argument("--adjudications", type=Path, default=Path("ai_eval/adjudications.csv"))
    parser.add_argument("--output", type=Path, default=Path("ai_eval/private_cases.generated.jsonl"))
    args = parser.parse_args()
    sources = load_jsonl(args.sources)
    source_ids = [str(row.get("id", "")) for row in sources]
    if not sources or any(not case_id for case_id in source_ids) or len(set(source_ids)) != len(source_ids):
        parser.error("The source manifest must contain unique, non-empty case IDs.")
    reviewer_a, reviewer_b = load_csv(args.reviewer_a), load_csv(args.reviewer_b)
    expected_ids = set(source_ids)
    if set(reviewer_a) != expected_ids or set(reviewer_b) != expected_ids:
        raise ValueError("Both reviewers must label every source exactly once; no extra IDs are allowed.")
    labels_a = {case_id: parse_annotation(row, case_id, "reviewer A") for case_id, row in reviewer_a.items()}
    labels_b = {case_id: parse_annotation(row, case_id, "reviewer B") for case_id, row in reviewer_b.items()}
    reviewer_ids = {item["reviewer_id"] for item in (*labels_a.values(), *labels_b.values())}
    ids_a = {item["reviewer_id"] for item in labels_a.values()}
    ids_b = {item["reviewer_id"] for item in labels_b.values()}
    if len(ids_a) != 1 or len(ids_b) != 1 or ids_a == ids_b:
        raise ValueError("Each sheet must have one consistent, distinct reviewer ID.")
    adjudications = load_csv(args.adjudications) if args.adjudications.exists() else {}
    if not set(adjudications).issubset(expected_ids):
        raise ValueError("Adjudication sheet contains a case absent from the source manifest.")

    output = []
    adjudicated_count = 0
    agreement_count = 0
    for source in sources:
        validate_source(source)
        case_id = str(source["id"])
        left, right = labels_a[case_id], labels_b[case_id]
        if (left["scenario"], left["language"], left["expected_threat"], left["expected_categories"]) == (right["scenario"], right["language"], right["expected_threat"], right["expected_categories"]):
            final = left
            if case_id in adjudications:
                raise ValueError(f"Case {case_id} has an unnecessary adjudication; remove it or resolve the reviewer disagreement first.")
            agreement_count += 1
            adjudicator_id = None
        else:
            if case_id not in adjudications:
                raise ValueError(f"Case {case_id} has reviewer disagreement and needs an adjudication.")
            decision = adjudications[case_id]
            adjudicator_id = (decision.get("adjudicator_id") or "").strip()
            if not adjudicator_id or adjudicator_id in reviewer_ids:
                raise ValueError(f"Case {case_id} needs a distinct third-reviewer ID.")
            scenario = (decision.get("scenario") or "").strip()
            language = (decision.get("language") or "").strip().lower()
            if scenario not in SCENARIOS or language not in LANGUAGES:
                raise ValueError(f"Adjudicated scenario or language is invalid for case {case_id}.")
            final = {"scenario": scenario, "language": language,
                     "expected_threat": parse_bool(decision.get("expected_threat"), case_id, "adjudication sheet"),
                     "expected_categories": parse_categories(decision.get("expected_categories"), case_id, "adjudication sheet")}
            if final["expected_threat"] != bool(final["expected_categories"]):
                raise ValueError(f"Adjudicated threat/no-threat and category labels disagree for case {case_id}.")
            adjudicated_count += 1
        record = {key: value for key, value in source.items() if key in {
            "id", "source_type", "consent_reference", "source_reference", "license", "text", "file", "expected_text"
        } and value not in (None, "")}
        record.update({"scenario": final["scenario"], "language": final["language"],
                       "expected_threat": final["expected_threat"],
                       "expected_categories": final["expected_categories"],
                       "reviewers": [next(iter(ids_a)), next(iter(ids_b))] + ([adjudicator_id] if adjudicator_id else []),
                       "reviewer_labels": [
                           {"reviewer_id": left["reviewer_id"], "expected_threat": left["expected_threat"], "expected_categories": left["expected_categories"], "scenario": left["scenario"], "language": left["language"]},
                           {"reviewer_id": right["reviewer_id"], "expected_threat": right["expected_threat"], "expected_categories": right["expected_categories"], "scenario": right["scenario"], "language": right["language"]},
                       ]})
        if adjudicator_id:
            record["adjudicator_id"] = adjudicator_id
            record["adjudicated_threat"] = final["expected_threat"]
            record["adjudicated_categories"] = final["expected_categories"]
        output.append(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output), encoding="utf-8")
    print(f"Merged {len(output)} case(s): {agreement_count} reviewer agreements and {adjudicated_count} adjudications.")
    print("No case text or evidence paths were printed. Review the local output before using it for evaluation.")


if __name__ == "__main__":
    main()
