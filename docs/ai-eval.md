# AI Evaluation

## Purpose

The AI evaluation set checks:

- entity extraction
- threat classification
- false positives
- Hindi inputs
- Kannada inputs

## Current evaluation set

The initial synthetic evaluation set contains 10 cases.

Each case records:

- language
- input text
- expected entities
- expected threat categories

## Running the evaluation

From the repository root:

```powershell
python ai_eval/run_eval.py