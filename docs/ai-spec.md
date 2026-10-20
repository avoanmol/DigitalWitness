# DigitalWitness AI Specification

## Purpose

The AI pipeline converts unstructured digital evidence into structured
investigation leads.

The AI can produce:

- entities
- threat flags
- suggested case links

AI output is advisory and always requires human review.

## Entity Extraction

Supported entities:

- email
- phone
- handle
- URL

Every entity contains:

- type
- value
- confidence
- exact source snippet

Entity snippets must occur verbatim in the evidence.

## Normalization

Entities are normalized before comparison.

Supported normalization includes:

- Unicode normalization
- phone normalization
- email normalization
- handle normalization
- URL normalization

Normalization allows equivalent representations to be compared
during case linking.

## Threat Classification

Supported threat categories:

- violence_threat
- harassment_stalking
- extortion_blackmail
- hate_speech
- fraud_scam
- self_harm_risk

Each threat flag contains:

- category
- severity
- confidence
- exact source snippet

Severity levels:

- critical
- high
- medium
- low

Self-harm risk requires human review.

## Case Linking

Cases can receive suggested links when they share a normalized entity.

Base confidence:

- phone: 0.90
- email: 0.90
- handle: 0.70
- URL: 0.60

Each additional shared entity adds 0.05.

Maximum confidence is 0.99.

Generic/common entities are ignored.

Links remain suggestions until a human confirms them.

Rejected links are not re-suggested.

## Pipeline

The analysis pipeline:

1. receives evidence text
2. extracts entities
3. classifies threats
4. validates snippets
5. stores generated results
6. updates analysis status

Failures produce a failed analysis result instead of blocking evidence
processing.

## Idempotency

Analysis and link jobs use deterministic job keys.

Running the same job again must not create duplicate results.

## Evaluation

The AI evaluation set includes:

- entity extraction cases
- threat classification cases
- safe/no-threat cases
- Hindi cases
- Kannada cases

False positives must be reviewed by a human.

## Human Review

AI output is never automatically confirmed.

Entities, threats, and case links remain pending until reviewed.

Confidence must be visible to investigators.

## Security

The AI layer must not:

- expose secrets
- log sensitive evidence unnecessarily
- invent evidence
- invent snippets
- automatically make investigative decisions

Hosted LLM processing should use synthetic or consented data during
the MVP.