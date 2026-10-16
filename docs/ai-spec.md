# DigitalWitness AI Specification

## Purpose

The AI subsystem converts unstructured digital evidence into structured
leads that can be reviewed by a human investigator.

AI output is a lead, not a verdict.

## Initial outputs

The AI system should identify:

- entities
- threat flags
- confidence
- supporting evidence snippets

## Entities

Initial entity types include:

- handles/usernames
- phone numbers
- email addresses
- URLs

Entity extraction should use deterministic methods such as regex where
possible, with the LLM used for additional context or extraction.

## Threat flags

Each threat flag should contain:

- category
- severity
- confidence
- verbatim supporting snippet

The system must not automatically take action based on a threat flag.

## Confidence

Confidence values are represented between 0 and 1.

Example:

- 0.95 = high confidence
- 0.50 = uncertain
- 0.10 = very low confidence

## Evidence snippets

Every snippet returned by the AI must be a verbatim substring of the
original evidence text.

The system should reject or flag snippets that do not occur in the
original source.

## Human review

AI results are suggestions for human investigators.

The AI must never automatically confirm an entity, threat, or case link.

## Safety

The system must not expose secrets or API keys in logs.

Real personal data should not be sent to a hosted LLM during development
unless the data is explicitly approved for that purpose.

Synthetic or consented data should be used for the MVP.

## LLM availability

The AI subsystem should support an LLM_ENABLED switch so that the
application can run without the hosted LLM.

## Evaluation

The AI should be evaluated using a labelled test set.

Evaluation should include:

- precision
- recall
- confusion by class
- false-positive tracking
- Hindi examples
- Kannada examples
- mixed-script/Hinglish examples