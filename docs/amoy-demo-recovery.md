# Amoy demo recovery record

Reviewed on 2026-10-29 after recovering the pending evidence anchor.

## Recovered evidence

- The previous submitted attempt was recorded on local Hardhat, chain `31337`; its transaction had no receipt on the configured Amoy RPC.
- The attempt was moved to `failed` through the audited recovery path with reason code `wrong_chain_id`. Its proof row was released and its evidence remained stored for retry.
- The integrity worker submitted a new one-leaf batch to Polygon Amoy, chain `80002`. The batch is confirmed, the evidence is anchored, and verification of the stored file and Merkle proof returned `verified`.
- Amoy transaction: `0xa4ef73e9e0cfbf6446cd5f5371376cb271a9b2c45ed1b81f6d108806901b76e5`.
- The audit hash chain verified successfully after recovery.

The default app and worker now expect chain `80002` and reject a different RPC chain before submission. Chain `31337` is only configured by the explicit local test profile.

## Older failed-batch history

- The database contains 182 older failed batches on chain `80002`: 14 dated October 25 and 168 dated October 28. None currently retains proof rows.
- There are 219 `anchor_failed` audit events. Eighty-nine of the current failed batches have no matching event by batch ID.
- The older audit details record retryability and evidence count, but not the cause. Do not infer a technical cause or delete these rows as cleanup; retain them as history until their origin is understood.
- One previously confirmed batch on local Hardhat, chain `31337`, remains as historical data. It is not an Amoy anchor and was left unchanged to preserve the recorded history. When checked from Amoy, the app now reports a chain-mismatch `error`, not `altered`.

## AI validation status

No source manifest or completed two-reviewer annotation files were found in the repository during this review. Synthetic evaluation results are development checks only and are not real-world accuracy evidence. Run the private evaluation only after confirming the external dataset’s consent/licensing and pointing the evaluator at de-identified cases with both reviewers’ completed labels.
