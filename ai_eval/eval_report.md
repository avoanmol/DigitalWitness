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
| Overall | 28 | 6 | 6 | 14 | 2 | 50.0% | 30.0% | 37.5% |
| defamation_morphing | 4 | 0 | 0 | 4 | 0 | n/a | 0.0% | 0.0% |
| extortion_blackmail | 4 | 3 | 0 | 1 | 0 | 100.0% | 75.0% | 85.7% |
| fake_profile_impersonation | 4 | 2 | 0 | 2 | 0 | 100.0% | 50.0% | 66.7% |
| harassment_stalking | 4 | 0 | 0 | 4 | 0 | n/a | 0.0% | 0.0% |
| hard_negative | 8 | 0 | 6 | 0 | 2 | 0.0% | n/a | 0.0% |
| intimate_image_abuse | 4 | 1 | 0 | 3 | 0 | 100.0% | 25.0% | 40.0% |

### By language

| Language | Cases | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| en | 14 | 3 | 2 | 7 | 2 | 60.0% | 30.0% |
| hi | 7 | 1 | 2 | 4 | 0 | 33.3% | 20.0% |
| kn | 7 | 2 | 2 | 3 | 0 | 50.0% | 40.0% |

## Local private-data pilot

The local file supplied 1 labeled case(s). Observed precision: n/a; recall: 0.0%; F1: 0.0%.
This small pilot is not an accuracy estimate. Consent, license and reviewer metadata are self-declared and were not independently verified.
Separate labels from two or more reviewers were recorded for 0/1 cases; unanimous agreement was n/a (0/0 cases with individual labels).
Cases without individual reviewer labels: 1. Reviewer IDs and individual case data are not published.
Exploratory coverage target (at least five threat and five non-threat cases in each of five core scenarios): 0/5 scenarios met.
Meeting this coverage target does not make the sample representative or establish real-world accuracy.
The report includes aggregate counts only; case text and local file paths are omitted.

## OCR fixtures

Evaluated 4 of 4 generated fixtures (2 screenshots, 2 scanned PDFs).
Mean character error rate: 1.7%.
Threat cue decisions matched: 4/4.

## Limitations

- Results measure these synthetic examples only and do not estimate real-world accuracy.
- The challenge set is hand-authored and small; it is not representative of real cases.
- The OCR benchmark has four generated fixtures and is too small for a deployment claim.
- Automated flags are review leads and must not be used as findings or criminal predictions.

To measure real-world performance, evaluate a separate, consented and de-identified set of representative evidence, with labels reviewed by independent humans. Keep it separate from examples used to tune rules and report false positives and false negatives by language and file type.

This tool provides investigative leads for human review; it does not authenticate media, determine whether a crime occurred, or predict criminality.
