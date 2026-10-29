# Local blind annotation workflow

This workflow creates two separate local review sheets, then combines labels into the evaluator's JSONL format. It does not upload evidence or call a model. Keep the source manifest, generated CSVs, evidence files, and output JSONL local and out of Git.

## Collect and prepare

1. Use only consented, de-identified material or public data whose license clearly permits this evaluation. Use random case IDs. Do not collect intimate images; redacted text or consented descriptions are enough for that scenario.
2. Put reviewed transcripts or local file paths under `ai_eval/private_assets/`. Create `ai_eval/private_sources.jsonl` with one JSON object per item. For text, include `text`; for an image/PDF, include `file` such as `private_assets/item-001.png`. Each row must include a permitted `source_type` and its non-identifying consent reference or public source/license.
3. Generate two separate sheets, one per pseudonymous reviewer ID:

   `python ai_eval/prepare_annotations.py --reviewer-a R1 --reviewer-b R2`

4. Give each reviewer their own CSV and access to the same de-identified source, without model output or the other reviewer's labels. They fill `scenario`, `language`, `expected_threat` (`true`/`false`), and `expected_categories`. Category values are semicolon-separated from `cyberstalking_bullying`, `blackmail_threatening`, `intimate_image_abuse`, `defamation_morphing`, `fake_profile_impersonation`, and `other`. Leave categories blank for a no-threat case; use `other` for a threat that does not fit the five core categories. Do not reuse reviewer IDs for the adjudicator.

## Label consistently

- `expected_threat=true` only when the evidence contains a concrete threat, coercion, targeted harassment, or other defined risk cue. Mentioning a topic in news, safety advice, satire, or support content alone is `false`.
- Use one scenario: `harassment_stalking`, `extortion_blackmail`, `intimate_image_abuse`, `fake_profile_impersonation`, `defamation_morphing`, or `other`.
- Record the language of the reviewed evidence as `en`, `hi`, or `kn`. The tool evaluates threat/no-threat labels; it does not decide authenticity or criminality.
- Select every category supported by the source, not just the reporter's chosen focus. Use an empty category list only when the reviewed material does not contain a threat or targeted harassment.
- If either reviewer disagrees on threat, category, scenario, or language, a third reviewer independently adjudicates in `ai_eval/adjudications.csv` with columns `case_id,adjudicator_id,scenario,language,expected_threat,expected_categories` (semicolon-separated categories).

### Category guidance

- `cyberstalking_bullying`: repeated unwanted contact, monitoring, following, targeted humiliation, or intimidation.
- `blackmail_threatening`: coercion, threats, or demands involving money, action, or exposure.
- `intimate_image_abuse`: threatened or non-consensual distribution of intimate imagery. Do not include intimate images in this evaluation set; use a consented, de-identified description or transcript.
- `defamation_morphing`: targeted false factual claims or an allegation that imagery was altered. A reviewer must not infer that an image is fake from appearance alone.
- `fake_profile_impersonation`: evidence indicates an account is pretending to be a real person; disclosed parody or fiction alone does not qualify.
- `other`: a threat or targeted harassment is present but none of the five categories describes it.

Safety advice, support, news reporting, fictional dialogue, and hypothetical examples are not threat labels by themselves. Label only what the reviewed source supports; these labels do not determine authenticity, intent, guilt, or criminality.

After both sheets are complete, merge locally:

`python ai_eval/merge_annotations.py`

The output defaults to `ai_eval/private_cases.generated.jsonl`; it does not overwrite the current evaluation dataset. Inspect it locally, then copy it to `ai_eval/private_cases.jsonl` when you are ready to run the private pilot. The report contains aggregate binary and per-category counts only; the category evaluator requires independent category labels from both reviewers.
