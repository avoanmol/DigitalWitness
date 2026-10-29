"""Create two private, blind annotation CSVs from a local source manifest."""
import argparse
import csv
import json
from pathlib import Path


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=Path("ai_eval/private_sources.jsonl"))
    parser.add_argument("--reviewer-a", required=True, help="Pseudonymous reviewer ID for the first blind copy")
    parser.add_argument("--reviewer-b", required=True, help="Different pseudonymous reviewer ID for the second blind copy")
    parser.add_argument("--out-dir", type=Path, default=Path("ai_eval"))
    args = parser.parse_args()
    if not args.reviewer_a.strip() or not args.reviewer_b.strip() or args.reviewer_a == args.reviewer_b:
        parser.error("Provide two distinct, non-identifying reviewer IDs.")
    sources = load_rows(args.sources)
    ids = [str(row.get("id", "")) for row in sources]
    if not sources or any(not item for item in ids) or len(set(ids)) != len(ids):
        parser.error("The local source manifest must contain unique, non-empty case IDs.")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fields = ["case_id", "reviewer_id", "evidence_text", "evidence_file", "scenario", "language", "expected_threat", "expected_categories", "notes"]
    for reviewer, suffix in ((args.reviewer_a, "a"), (args.reviewer_b, "b")):
        path = args.out_dir / f"reviewer_{suffix}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in sources:
                writer.writerow({
                    "case_id": row["id"], "reviewer_id": reviewer,
                    "evidence_text": row.get("text", ""), "evidence_file": row.get("file", ""),
                    "scenario": "", "language": "", "expected_threat": "", "expected_categories": "", "notes": "",
                })
    print(f"Created two local annotation sheets for {len(sources)} case(s). Evidence text and file paths were not printed.")
    print(f"Keep ai_eval/reviewer_a.csv and ai_eval/reviewer_b.csv local and out of Git.")


if __name__ == "__main__":
    main()
