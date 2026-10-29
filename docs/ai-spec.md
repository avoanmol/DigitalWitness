# AI analysis and case linking

## What runs

Evidence uploads create an `analyse` job in the shared PostgreSQL queue. The separate `ai-worker` container extracts selectable PDF text, optionally sends PDF text or image bytes to an OpenAI-compatible vision/chat endpoint, validates returned JSON, extracts normalized entities, and queues a `link` job. The worker runs without blockchain RPC configuration.

With `LLM_ENABLED=false` (the default), selectable PDF text uses local rules for entity extraction and conservative phrase-plus-context category suggestions. English review patterns consider combinations of scenario, action, and target cues; they remain triage leads and can miss context, wording variants, sarcasm, or non-English phrasing. The rules do not decide intent, identity, guilt, or whether an image is authentic. JPEG/PNG/WEBP and scanned PDF pages use local Tesseract OCR when the binary and requested language data are installed; PDF OCR is limited to the first five pages. Without those OCR dependencies, analysis reports that text could not be extracted. MP4, MOV, and WEBM processing samples video frames; audio tracks are not transcribed. An optional vision model can add image/video interpretation, but does not authenticate the media. With the LLM enabled, evidence content and the selected focus labels are sent to the configured provider; use only a provider/account approved for the evidence data. Invalid JSON, provider timeouts, and provider errors fall back to local rules and never block upload.

## Results and review

Results use the existing `analyses`, `entities`, `threat_flags`, and `case_links` tables. Emails and handles are case-folded, Indian phone numbers normalize to E.164, and URLs normalize host/path. Common platform URLs are excluded from matching. Links require a matching normalized entity in different cases; self-links and duplicate pairs are rejected.

Threat snippets must be exact substrings of analyzed text. Every threat flag starts `pending`; every AI link starts `suggested`. Only investigator/admin can confirm or reject either item. No model output changes evidence integrity or auto-confirms a relationship. Human review decisions are audited.

## API

- `GET /evidence/{id}/analysis`
- `POST /evidence/{id}/analyse` queues or retries analysis
- `PATCH /flags/{id}` with `{ "review_status": "confirmed" | "rejected", "review_reason": "..." }`
- `GET /cases/{id}/links`
- `GET /cases/{id}/investigative-summary` returns an audited, deterministic case rollup
- `POST /links` with `case_a_id`, `case_b_id`, and optional `note`
- `PATCH /links/{id}` with `{ "status": "confirmed" | "rejected" }`

Analysis/link reads require investigator, legal, or admin roles. Review and manual link creation require investigator or admin. Flag reviews must include a structured reason; no evidence text is copied into the feedback label.

## Local configuration

Leave `LLM_ENABLED=false` for local OCR and rules-only operation. To enable model-assisted image/video interpretation and classification, set `LLM_ENABLED=true`, `LLM_API_KEY`, and optionally `LLM_MODEL`/`LLM_BASE_URL` in the uncommitted local `.env`, then rebuild/restart Compose. The example file contains no live key. Tesseract and its language data must also be installed for OCR.

## Synthetic evaluation

`ai_eval/samples.jsonl` contains 60 fictional examples, split evenly among English, Hindi, and Kannada. `ai_eval/fictional_scenario_set.jsonl` adds 200 author-written English cases across the five product scenarios, including non-threat examples. The existing synthetic measurements are development checks only, not evidence of real-world accuracy; the fictional cases have not been independently reviewed and do not validate media authenticity or deepfake detection.


## OCR, video, provenance, and evaluation

- JPEG, PNG, and WEBP evidence uses Tesseract OCR with the configured `OCR_LANGUAGES`. Analysis reports limited file metadata observations and dimensions. It does not retain GPS coordinates, creator/software strings, or timestamp values.
- PDFs use embedded text when available and OCR for scanned pages, up to the first five pages. The report may include page count and whether selected creator/producer/date metadata fields are present; values are not treated as trusted.
- MP4, MOV, and WEBM uploads are limited to 60 seconds. FFmpeg samples at most four evenly spaced frames, scales them to a maximum 1280×720, and runs OCR on those frames. If an LLM is configured, only those sampled frames (up to four) and extracted text are sent for analysis. Results identify this sampling limit. Audio tracks are preserved as evidence but are not transcribed or analyzed.
- Video and image metadata can be absent, edited, or spoofed. Metadata presence is an observation, not an authenticity signal. Sparse video samples cannot establish continuity or represent the full recording.
- OCR work is bounded by image pixel and execution-time limits; video decoding has per-command time limits and a four-frame ceiling.
- The selected investigation focus is passed to the configured model as context only; it cannot by itself trigger a finding. The model is instructed to use the project’s five harassment categories and not to claim media authenticity.
- The analysis response records the extraction method and selected investigation focus.
- MP3, WAV, and M4A files are accepted and preserved, but the analysis worker does not currently perform speech recognition or produce audio transcripts.
- `ai_eval` uses synthetic multilingual text plus generated screenshot and scanned-PDF fixtures. Its OCR character-error rate and threat cue matches are demonstrations, not accuracy guarantees.

## Context, coverage, and case overview

- Phrase matches are never silently removed because of context cues. If the same sentence contains a possible negation, quote/reporting cue, or educational/hypothetical cue, the flag receives a lower uncalibrated review score and an explicit caution. A human checks the surrounding source before labeling it.
- Each analysis records a `coverage` object describing extracted character count, processing truncation, pages/frames examined where available, and limits or extraction failures. This is processing coverage, not a quality or accuracy score.
- `GET /cases/{id}/investigative-summary` returns a deterministic, evidence-linked rollup of saved flags, selected focus labels, review status, and analysis coverage. It does not generate a narrative finding or infer that a reported event occurred. Investigator, legal, and admin reads are audited.
- Flag review requires a structured reason. The latest reason is retained with the analysis record and each review event records it in the append-only audit log. These human labels are useful for error analysis; they do not automatically retrain the rules or model.
