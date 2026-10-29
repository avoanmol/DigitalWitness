"""Run the labelled synthetic evaluation and write ai_eval/eval_report.json."""
from __future__ import annotations
import io
import json
import textwrap
from pathlib import Path
from backend.app.ai.extract import detect_language, extract_document_text, extract_entities
from backend.app.ai.normalise import normalise_entity
from backend.app.ai.threats import detect_threats
from backend.app.ai.categories import INVESTIGATION_CATEGORIES
ROOT = Path(__file__).resolve().parent
THREAT_CATEGORIES = (*INVESTIGATION_CATEGORIES, "other")

def ratio(numerator: int, denominator: int):
    return round(numerator / denominator, 4) if denominator else None


def _binary_metrics(expected: list[bool], predicted: list[bool]) -> dict:
    tp = sum(want and got for want, got in zip(expected, predicted))
    fp = sum(not want and got for want, got in zip(expected, predicted))
    fn = sum(want and not got for want, got in zip(expected, predicted))
    tn = sum(not want and not got for want, got in zip(expected, predicted))
    precision, recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
    f1 = ratio(2 * tp, 2 * tp + fp + fn)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision,
            "recall": recall, "f1": f1, "specificity": ratio(tn, tn + fp)}


def _category_metrics(rows: list[dict]) -> dict:
    labelled = [row for row in rows if row.get("expected_categories") is not None]
    if not labelled:
        return {"status": "category_labels_not_provided", "case_count": 0, "by_category": {}}
    by_category = {}
    expected_flat: list[bool] = []
    predicted_flat: list[bool] = []
    for category in THREAT_CATEGORIES:
        expected = [category in row["expected_categories"] for row in labelled]
        predicted = [category in row["predicted_categories"] for row in labelled]
        by_category[category] = _binary_metrics(expected, predicted)
        expected_flat.extend(expected)
        predicted_flat.extend(predicted)
    f1_values = [item["f1"] for item in by_category.values() if item["f1"] is not None]
    return {
        "status": "evaluated",
        "case_count": len(labelled),
        "micro": _binary_metrics(expected_flat, predicted_flat),
        "macro_f1": round(sum(f1_values) / len(f1_values), 4) if f1_values else None,
        "by_category": by_category,
    }

def _cer(expected: str, actual: str) -> float:
    left = "".join(char for char in expected.casefold() if char.isalnum())
    right = "".join(char for char in actual.casefold() if char.isalnum())
    if not left:
        return 0.0 if not right else 1.0
    previous = list(range(len(right) + 1))
    for row, char in enumerate(left, start=1):
        current = [row]
        for column, observed in enumerate(right, start=1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (char != observed)))
        previous = current
    return previous[-1] / len(left)


def _render_fixture(text: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO
    lines = textwrap.wrap(text, width=48) or [""]
    font = ImageFont.load_default(size=26)
    canvas = Image.new("RGB", (1100, max(180, 70 + 48 * len(lines))), "white")
    ImageDraw.Draw(canvas).multiline_text((36, 32), "\n".join(lines), fill="#111111", font=font, spacing=12)
    output = BytesIO()
    try:
        canvas.save(output, format="PNG")
        return output.getvalue()
    finally:
        canvas.close()


def _scanned_pdf(png: bytes) -> bytes:
    import pymupdf
    document = pymupdf.open()
    page = document.new_page(width=620, height=240)
    page.insert_image(page.rect, stream=png)
    try:
        return document.tobytes()
    finally:
        document.close()


def _run_ocr_eval() -> dict:
    fixtures = json.loads((ROOT / "ocr_cases.json").read_text(encoding="utf-8"))
    results, skipped = [], []
    for fixture in fixtures:
        try:
            png = _render_fixture(fixture["text"])
            data = _scanned_pdf(png) if fixture["format"] == "pdf" else png
            filename = fixture["id"] + (".pdf" if fixture["format"] == "pdf" else ".png")
            mime = "application/pdf" if fixture["format"] == "pdf" else "image/png"
            text, method = extract_document_text(data, filename, mime)
            detected = bool(detect_threats(text, detect_language(text)))
            results.append({"id": fixture["id"], "method": method, "cer": _cer(fixture["text"], text),
                            "expected_threat": fixture["expected_threat"], "detected_threat": detected,
                            "threat_match": detected == fixture["expected_threat"],
                            "text_extracted": bool(text.strip())})
        except (RuntimeError, ImportError, OSError) as exc:
            skipped.append({"id": fixture["id"], "reason": str(exc)})
            if skipped:
                break
    evaluated = results
    return {"fixture_count": len(fixtures), "evaluated_count": len(evaluated), "skipped": skipped,
            "formats": {kind: sum(item["format"] == kind for item in fixtures) for kind in ("png", "pdf")},
            "mean_cer": round(sum(item["cer"] for item in evaluated) / len(evaluated), 4) if evaluated else None,
            "threat_matches": sum(item["threat_match"] for item in evaluated),
            "threat_metrics": _binary_metrics([item["expected_threat"] for item in evaluated],
                                               [item["detected_threat"] for item in evaluated]),
            "results": results}


def _run_challenge_eval() -> dict:
    cases = [json.loads(line) for line in (ROOT / "challenge_cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for case in cases:
        predicted = bool(detect_threats(case["text"], detect_language(case["text"])))
        results.append({"id": case["id"], "language": case["language"], "scenario": case["scenario"],
                        "expected_threat": bool(case["expected_threat"]), "predicted_threat": predicted})
    def grouped_metrics(key: str) -> dict:
        groups = sorted({case[key] for case in cases})
        output = {}
        for group in groups:
            selected = [row for row in results if row[key] == group]
            output[group] = {"samples": len(selected), **_binary_metrics(
                [row["expected_threat"] for row in selected],
                [row["predicted_threat"] for row in selected],
            )}
        return output
    return {
        "name": "held-out synthetic challenge set",
        "count": len(cases),
        "labeling": "Hand-authored synthetic cases labeled by the project team; no independent annotator review.",
        "overall": _binary_metrics([row["expected_threat"] for row in results],
                                   [row["predicted_threat"] for row in results]),
        "by_scenario": grouped_metrics("scenario"),
        "by_language": grouped_metrics("language"),
        "errors": [row for row in results if row["expected_threat"] != row["predicted_threat"]],
    }


def _run_private_eval() -> dict:
    dataset = ROOT / "private_cases.jsonl"
    if not dataset.exists():
        return {"status": "not_provided", "case_count": 0}

    cases = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    required_scenarios = {"harassment_stalking", "extortion_blackmail", "intimate_image_abuse",
                          "fake_profile_impersonation", "defamation_morphing", "other"}
    seen_ids: set[str] = set()
    results: list[dict] = []
    review_audits: list[dict] = []
    cer_values: list[float] = []
    extraction_methods: dict[str, int] = {}
    for case in cases:
        case_id = str(case.get("id", ""))
        if not case_id or case_id in seen_ids:
            raise ValueError("Private evaluation case IDs must be present and unique.")
        seen_ids.add(case_id)
        source_type = case.get("source_type")
        if source_type not in {"consented_redacted", "licensed_public"}:
            raise ValueError(f"Private evaluation case {case_id} must declare a consented or licensed source.")
        if source_type == "consented_redacted" and not str(case.get("consent_reference", "")).strip():
            raise ValueError(f"Private evaluation case {case_id} needs a non-identifying consent reference.")
        if source_type == "licensed_public" and not all(str(case.get(key, "")).strip() for key in ("source_reference", "license")):
            raise ValueError(f"Private evaluation case {case_id} needs its source reference and license.")
        reviewers = case.get("reviewers", [])
        if (not isinstance(reviewers, list) or any(not isinstance(item, str) or not item.strip() for item in reviewers)
                or len(set(reviewers)) < 2):
            raise ValueError(f"Private evaluation case {case_id} needs two distinct reviewer IDs.")
        if case.get("language") not in {"en", "hi", "kn"}:
            raise ValueError(f"Private evaluation case {case_id} language must be en, hi or kn.")
        if case.get("scenario") not in required_scenarios:
            raise ValueError(f"Private evaluation case {case_id} has an unsupported scenario label.")
        expected = case.get("expected_threat")
        if not isinstance(expected, bool):
            raise ValueError(f"Private evaluation case {case_id} needs a boolean expected_threat label.")
        expected_categories = case.get("expected_categories")
        if expected_categories is not None:
            if (not isinstance(expected_categories, list)
                    or any(not isinstance(item, str) or item not in THREAT_CATEGORIES for item in expected_categories)
                    or len(set(expected_categories)) != len(expected_categories)):
                raise ValueError(f"Private evaluation case {case_id} expected_categories must be a unique list of supported categories.")
            if expected != bool(expected_categories):
                raise ValueError(f"Private evaluation case {case_id} expected_categories must agree with expected_threat.")

        reviewer_labels = case.get("reviewer_labels")
        if reviewer_labels is None:
            if expected_categories is not None:
                raise ValueError(f"Private evaluation case {case_id} category labels need independent reviewer labels.")
            review_audits.append({"recorded": False, "unanimous": None, "category_recorded": False, "category_unanimous": None})
        else:
            if (not isinstance(reviewer_labels, list) or len(reviewer_labels) < 2
                    or any(not isinstance(item, dict)
                           or not isinstance(item.get("reviewer_id"), str)
                           or not item["reviewer_id"].strip()
                           or not isinstance(item.get("expected_threat"), bool)
                           for item in reviewer_labels)):
                raise ValueError(f"Private evaluation case {case_id} reviewer_labels must contain at least two reviewer IDs and boolean labels.")
            label_ids = [item["reviewer_id"].strip() for item in reviewer_labels]
            if len(set(label_ids)) < 2 or not set(label_ids).issubset(set(reviewers)):
                raise ValueError(f"Private evaluation case {case_id} reviewer_labels must identify two distinct listed reviewers.")
            category_labels = []
            for item in reviewer_labels:
                categories = item.get("expected_categories")
                if categories is not None:
                    if (not isinstance(categories, list)
                            or any(not isinstance(category, str) or category not in THREAT_CATEGORIES for category in categories)
                            or len(set(categories)) != len(categories)
                            or item["expected_threat"] != bool(categories)):
                        raise ValueError(f"Private evaluation case {case_id} has invalid reviewer category labels.")
                category_labels.append(tuple(sorted(categories)) if categories is not None else None)
            category_recorded = all(item is not None for item in category_labels)
            category_unanimous = len(set(category_labels)) == 1 if category_recorded else None
            if expected_categories is not None and not category_recorded:
                raise ValueError(f"Private evaluation case {case_id} needs category labels from both reviewers.")
            if category_recorded and expected_categories is None:
                raise ValueError(f"Private evaluation case {case_id} reviewer categories need a final expected_categories label.")
            label_values = [(
                item["expected_threat"], item.get("scenario"), item.get("language"),
                category_labels[index],
            ) for index, item in enumerate(reviewer_labels)]
            unanimous = len(set(label_values)) == 1
            adjudicated = case.get("adjudicated_threat")
            adjudicated_categories = case.get("adjudicated_categories")
            if unanimous:
                if expected != reviewer_labels[0]["expected_threat"]:
                    raise ValueError(f"Private evaluation case {case_id} expected_threat must match unanimous reviewer labels.")
                if case["scenario"] != reviewer_labels[0].get("scenario") or case["language"] != reviewer_labels[0].get("language"):
                    raise ValueError(f"Private evaluation case {case_id} scenario and language must match unanimous reviewer labels.")
                if expected_categories is not None and tuple(sorted(expected_categories)) != category_labels[0]:
                    raise ValueError(f"Private evaluation case {case_id} expected_categories must match unanimous reviewer labels.")
            if not unanimous:
                adjudicator_id = case.get("adjudicator_id")
                if (not isinstance(adjudicated, bool) or expected != adjudicated
                        or not isinstance(adjudicator_id, str) or not adjudicator_id.strip()
                        or adjudicator_id.strip() not in reviewers or adjudicator_id.strip() in label_ids):
                    raise ValueError(f"Private evaluation case {case_id} with reviewer disagreement needs a distinct listed adjudicator and matching boolean adjudicated_threat.")
                if expected_categories is not None and (
                    not isinstance(adjudicated_categories, list)
                    or any(not isinstance(item, str) or item not in THREAT_CATEGORIES for item in adjudicated_categories)
                    or tuple(sorted(adjudicated_categories)) != tuple(sorted(expected_categories))
                ):
                    raise ValueError(f"Private evaluation case {case_id} needs adjudicated_categories matching its final category labels.")
            review_audits.append({"recorded": True, "unanimous": unanimous,
                                  "category_recorded": category_recorded,
                                  "category_unanimous": category_unanimous})

        if isinstance(case.get("text"), str):
            text = case["text"]
            method = "reviewed_transcript"
            media_type = "text"
        elif isinstance(case.get("file"), str):
            file_path = (ROOT / case["file"]).resolve()
            private_assets = (ROOT / "private_assets").resolve()
            if private_assets not in file_path.parents or not file_path.is_file():
                raise ValueError(f"Private evaluation case {case_id} file must exist under ai_eval/private_assets/.")
            suffix = file_path.suffix.lower()
            mime = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(suffix)
            if mime is None:
                raise ValueError(f"Private evaluation case {case_id} has an unsupported file type.")
            text, method = extract_document_text(file_path.read_bytes(), file_path.name, mime)
            media_type = suffix.lstrip(".")
            if isinstance(case.get("expected_text"), str):
                cer_values.append(_cer(case["expected_text"], text))
        else:
            raise ValueError(f"Private evaluation case {case_id} needs text or a local evidence file.")

        extraction_methods[method] = extraction_methods.get(method, 0) + 1
        predictions = detect_threats(text, case["language"])
        results.append({"id": case_id, "language": case["language"], "scenario": case["scenario"],
                        "media_type": media_type, "expected_threat": expected,
                        "expected_categories": expected_categories,
                        "predicted_categories": sorted({item.threat_class for item in predictions}),
                        "predicted_threat": bool(predictions)})

    def group_metrics(key: str) -> dict:
        groups = sorted({row[key] for row in results})
        return {group: {
            "cases": sum(row[key] == group for row in results),
            "positive_labels": sum(row[key] == group and row["expected_threat"] for row in results),
            "negative_labels": sum(row[key] == group and not row["expected_threat"] for row in results),
            **_binary_metrics(
                [row["expected_threat"] for row in results if row[key] == group],
                [row["predicted_threat"] for row in results if row[key] == group],
            ),
        } for group in groups}

    core_scenarios = (
        "harassment_stalking", "extortion_blackmail", "intimate_image_abuse",
        "fake_profile_impersonation", "defamation_morphing",
    )
    target_per_class = 5
    pilot_coverage = {}
    for scenario in core_scenarios:
        selected = [row for row in results if row["scenario"] == scenario]
        positive_count = sum(row["expected_threat"] for row in selected)
        negative_count = sum(not row["expected_threat"] for row in selected)
        pilot_coverage[scenario] = {
            "positive_cases": positive_count,
            "negative_cases": negative_count,
            "target_per_class": target_per_class,
            "target_met": positive_count >= target_per_class and negative_count >= target_per_class,
        }

    reviewed_cases = sum(item["recorded"] for item in review_audits)
    unanimous_cases = sum(item["unanimous"] is True for item in review_audits)
    category_reviewed_cases = sum(item["category_recorded"] for item in review_audits)
    category_unanimous_cases = sum(item["category_unanimous"] is True for item in review_audits)
    def grouped_category_metrics(key: str) -> dict:
        groups = sorted({row[key] for row in results})
        return {group: _category_metrics([row for row in results if row[key] == group]) for group in groups}
    return {
        "status": "evaluated",
        "pilot_coverage": {
            "core_scenarios_met": sum(item["target_met"] for item in pilot_coverage.values()),
            "core_scenarios_total": len(core_scenarios),
            "target_met": all(item["target_met"] for item in pilot_coverage.values()),
            "by_scenario": pilot_coverage,
        },
        "case_count": len(results),
        "reviewer_labeled_cases": reviewed_cases,
        "reviewer_unanimous_cases": unanimous_cases,
        "reviewer_agreement": round(unanimous_cases / reviewed_cases, 4) if reviewed_cases else None,
        "cases_without_individual_labels": len(results) - reviewed_cases,
        "source_types": sorted({case["source_type"] for case in cases}),
        "reviewer_count_minimum": min((len(set(case["reviewers"])) for case in cases), default=0),
        "reviewer_category_labeled_cases": category_reviewed_cases,
        "reviewer_category_unanimous_cases": category_unanimous_cases,
        "reviewer_category_agreement": round(category_unanimous_cases / category_reviewed_cases, 4) if category_reviewed_cases else None,
        "overall": _binary_metrics([row["expected_threat"] for row in results],
                                   [row["predicted_threat"] for row in results]),
        "by_language": group_metrics("language"),
        "by_scenario": group_metrics("scenario"),
        "by_media_type": group_metrics("media_type"),
        "category_metrics": _category_metrics(results),
        "categories_by_language": grouped_category_metrics("language"),
        "categories_by_scenario": grouped_category_metrics("scenario"),
        "categories_by_media_type": grouped_category_metrics("media_type"),
        "mean_ocr_cer": round(sum(cer_values) / len(cer_values), 4) if cer_values else None,
        "extraction_methods": extraction_methods,
    }


def run() -> dict:
    samples = [json.loads(line) for line in (ROOT / "samples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    report = {
        "dataset": "synthetic benchmark with optional separate private pilot",
        "dataset_scope": "Synthetic benchmark scores use only hand-authored examples. Private pilot data, when supplied, is evaluated separately and does not change those scores.",
        "real_world_accuracy_claim": False,
        "development_sample_count": len(samples),
        "development_by_language": {},
        "challenge": _run_challenge_eval(),
        "private_evaluation": _run_private_eval(),
        "ocr": _run_ocr_eval(),
        "limitations": [
            "Results measure these synthetic examples only and do not estimate real-world accuracy.",
            "The challenge set is hand-authored and small; it is not representative of real cases.",
            "The OCR benchmark has four generated fixtures and is too small for a deployment claim.",
            "Automated flags are review leads and must not be used as findings or criminal predictions.",
        ],
    }
    for language in ("en", "hi", "kn"):
        subset = [item for item in samples if item["language"] == language]
        etp = efp = efn = 0
        expected_threats, predicted_threats = [], []
        for item in subset:
            predicted = extract_entities(item["text"])
            matched = 0
            for entity in item["expected_entities"]:
                expected = normalise_entity(entity["type"], entity["raw"])
                if any(value.type == entity["type"] and value.normalised_value == expected for value in predicted):
                    matched += 1
            etp += matched
            efn += len(item["expected_entities"]) - matched
            efp += max(0, len(predicted) - matched)
            expected_threats.append(bool(item["expected_threat"]))
            predicted_threats.append(bool(detect_threats(item["text"], detect_language(item["text"]))))
        entity_precision, entity_recall = ratio(etp, etp + efp), ratio(etp, etp + efn)
        report["development_by_language"][language] = {
            "samples": len(subset),
            "entity": {"tp": etp, "fp": efp, "fn": efn,
                       "precision": entity_precision, "recall": entity_recall,
                       "f1": ratio(2 * etp, 2 * etp + efp + efn)},
            "threat": _binary_metrics(expected_threats, predicted_threats),
        }
    (ROOT / "eval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown(report)
    return report


def _display_percent(value):
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _write_markdown(report: dict) -> None:
    lines = [
        "# DigitalWitness AI and OCR evaluation",
        "",
        f"**Development examples:** {report['development_sample_count']} synthetic examples used during implementation.",
        f"**Held-out challenge examples:** {report['challenge']['count']} synthetic examples, reserved from rule tuning.",
        f"**Scope:** {report['dataset_scope']}",
        "**Real-world accuracy claim:** No.",
        "**Challenge labels:** Synthetic and project-team labeled; not independently annotated.",
        "",
        "## Held-out synthetic challenge results",
        "",
        "These examples are separate from the original development set. Labels were written by the project team, not independently reviewed.",
        "",
        "| Set | Cases | TP | FP | FN | TN | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    challenge = report["challenge"]
    overall = challenge["overall"]
    lines.append(f"| Overall | {challenge['count']} | {overall['tp']} | {overall['fp']} | {overall['fn']} | {overall['tn']} | "
                 f"{_display_percent(overall['precision'])} | {_display_percent(overall['recall'])} | {_display_percent(overall['f1'])} |")
    for scenario, values in challenge["by_scenario"].items():
        lines.append(f"| {scenario} | {values['samples']} | {values['tp']} | {values['fp']} | {values['fn']} | {values['tn']} | "
                     f"{_display_percent(values['precision'])} | {_display_percent(values['recall'])} | {_display_percent(values['f1'])} |")
    lines.extend(["", "### By language", "", "| Language | Cases | TP | FP | FN | TN | Precision | Recall |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for language, values in challenge["by_language"].items():
        lines.append(f"| {language} | {values['samples']} | {values['tp']} | {values['fp']} | {values['fn']} | {values['tn']} | "
                     f"{_display_percent(values['precision'])} | {_display_percent(values['recall'])} |")
    private_eval = report["private_evaluation"]
    lines.extend(["", "## Local private-data pilot", ""])
    if private_eval["status"] == "evaluated":
        overall_private = private_eval["overall"]
        lines.append(f"The local file supplied {private_eval['case_count']} labeled case(s). "
                     f"Observed precision: {_display_percent(overall_private['precision'])}; "
                     f"recall: {_display_percent(overall_private['recall'])}; F1: {_display_percent(overall_private['f1'])}.")
        lines.append("This small pilot is not an accuracy estimate. Consent, license and reviewer metadata are self-declared and were not independently verified.")
        lines.append(f"Separate labels from two or more reviewers were recorded for {private_eval['reviewer_labeled_cases']}/{private_eval['case_count']} cases; "
                     f"unanimous annotation agreement across the recorded labels was {_display_percent(private_eval['reviewer_agreement'])} "
                     f"({private_eval['reviewer_unanimous_cases']}/{private_eval['reviewer_labeled_cases']} cases with individual labels).")
        category_metrics = private_eval["category_metrics"]
        if category_metrics["status"] == "evaluated":
            lines.append(f"Category labels from two reviewers were available for {private_eval['reviewer_category_labeled_cases']} case(s); "
                         f"category agreement was {_display_percent(private_eval['reviewer_category_agreement'])}.")
            lines.extend(["", "### Category-level results", "",
                          "| Category | TP | FP | FN | TN | Precision | Recall | F1 |",
                          "|---|---:|---:|---:|---:|---:|---:|---:|"])
            for category, values in category_metrics["by_category"].items():
                lines.append(f"| {category} | {values['tp']} | {values['fp']} | {values['fn']} | {values['tn']} | "
                             f"{_display_percent(values['precision'])} | {_display_percent(values['recall'])} | {_display_percent(values['f1'])} |")
            lines.append("These category-level measurements apply only to the local reviewed cases shown here and are not real-world accuracy estimates.")
        else:
            lines.append("Category-level metrics are unavailable until both reviewers label each case with one or more categories (or an empty list for no threat).")
        lines.append(f"Cases without individual reviewer labels: {private_eval['cases_without_individual_labels']}. Reviewer IDs and individual case data are not published.")
        coverage = private_eval["pilot_coverage"]
        lines.append(f"Exploratory coverage target (at least five threat and five non-threat cases in each of five core scenarios): "
                     f"{coverage['core_scenarios_met']}/{coverage['core_scenarios_total']} scenarios met.")
        lines.append("Meeting this coverage target does not make the sample representative or establish real-world accuracy.")
        lines.append("The report includes aggregate counts only; case text and local file paths are omitted.")
    else:
        lines.append("Not run: no private consented/licensed dataset was provided.")
    ocr = report["ocr"]
    lines.extend([
        "", "## OCR fixtures", "",
        f"Evaluated {ocr['evaluated_count']} of {ocr['fixture_count']} generated fixtures "
        f"({ocr['formats'].get('png', 0)} screenshots, {ocr['formats'].get('pdf', 0)} scanned PDFs).",
        f"Mean character error rate: {_display_percent(ocr['mean_cer'])}.",
        f"Threat cue decisions matched: {ocr['threat_matches']}/{ocr['evaluated_count']}.",
        "", "## Limitations", "",
    ])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.extend([
        "", "To measure real-world performance, evaluate a separate, consented and de-identified set "
        "of representative evidence, with labels reviewed by independent humans. Keep it separate "
        "from examples used to tune rules and report false positives and false negatives by language and file type.",
        "", "This tool provides investigative leads for human review; it does not authenticate media, "
        "determine whether a crime occurred, or predict criminality.", "",
    ])
    (ROOT / "eval_report.md").write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Saved judge-facing report: {ROOT / 'eval_report.md'}")
