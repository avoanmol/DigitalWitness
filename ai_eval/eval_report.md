# DigitalWitness AI and OCR evaluation

**Development examples:** 60 synthetic examples used during implementation.
**Held-out challenge examples:** 28 synthetic examples, reserved from rule tuning.
**Scope:** Synthetic benchmark scores use only hand-authored examples. Private pilot data, when supplied, is evaluated separately and does not change those scores.
**Real-world accuracy claim:** No.
**Challenge labels:** Synthetic and project-team labeled; not independently annotated.

## Held-out synthetic challenge results

These examples are separate from the original development set. Labels were written by the project team, not independently reviewed.

| Set | Cases | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Overall | 28 | 11 | 1 | 9 | 7 | 91.7% | 55.0% | 68.8% |
| defamation_morphing | 4 | 1 | 0 | 3 | 0 | 100.0% | 25.0% | 40.0% |
| extortion_blackmail | 4 | 4 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| fake_profile_impersonation | 4 | 2 | 0 | 2 | 0 | 100.0% | 50.0% | 66.7% |
| harassment_stalking | 4 | 3 | 0 | 1 | 0 | 100.0% | 75.0% | 85.7% |
| hard_negative | 8 | 0 | 1 | 0 | 7 | 0.0% | n/a | 0.0% |
| intimate_image_abuse | 4 | 1 | 0 | 3 | 0 | 100.0% | 25.0% | 40.0% |

### By language

| Language | Cases | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| en | 14 | 8 | 1 | 2 | 3 | 88.9% | 80.0% |
| hi | 7 | 2 | 0 | 3 | 2 | 100.0% | 40.0% |
| kn | 7 | 1 | 0 | 4 | 2 | 100.0% | 20.0% |

## Local private-data pilot

The local file supplied 1 labeled case(s). Observed precision: n/a; recall: 0.0%; F1: 0.0%.
This small pilot is not an accuracy estimate. Consent, license and reviewer metadata are self-declared and were not independently verified.
Separate labels from two or more reviewers were recorded for 0/1 cases; unanimous annotation agreement across the recorded labels was n/a (0/0 cases with individual labels).
Category-level metrics are unavailable until both reviewers label each case with one or more categories (or an empty list for no threat).
Cases without individual reviewer labels: 1. Reviewer IDs and individual case data are not published.
Exploratory coverage target (at least five threat and five non-threat cases in each of five core scenarios): 0/5 scenarios met.
Meeting this coverage target does not make the sample representative or establish real-world accuracy.
The report includes aggregate counts only; case text and local file paths are omitted.

## OCR fixtures

Evaluated 0 of 4 generated fixtures (2 screenshots, 2 scanned PDFs).
Mean character error rate: n/a.
Threat cue decisions matched: 0/0.

## Limitations

- Results measure these synthetic examples only and do not estimate real-world accuracy.
- The challenge set is hand-authored and small; it is not representative of real cases.
- The OCR benchmark has four generated fixtures and is too small for a deployment claim.
- Automated flags are review leads and must not be used as findings or criminal predictions.

To measure real-world performance, evaluate a separate, consented and de-identified set of representative evidence, with labels reviewed by independent humans. Keep it separate from examples used to tune rules and report false positives and false negatives by language and file type.

This tool provides investigative leads for human review; it does not authenticate media, determine whether a crime occurred, or predict criminality.
