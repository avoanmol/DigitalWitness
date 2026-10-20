import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrity.batcher import (
    DEFAULT_ANCHOR_BATCH_SIZE,
    DEFAULT_ANCHOR_INTERVAL_SECONDS,
    anchor_evidence_records,
    retry_delay_after_failure,
    should_trigger_batch,
)
from app.integrity.chain import ChainError
from app.integrity.merkle import build_levels, get_proof, leaf_hash
from app.integrity.verify import verify_integrity


class BatcherTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
        self.records = [
            {
                "evidence_id": "evidence-b",
                "uploaded_at": self.start + timedelta(seconds=5),
                "file_sha256_hex": format(2, "064x"),
            },
            {
                "evidence_id": "evidence-z",
                "uploaded_at": self.start,
                "file_sha256_hex": format(3, "064x"),
            },
            {
                "evidence_id": "evidence-a",
                "uploaded_at": self.start,
                "file_sha256_hex": format(1, "064x"),
            },
        ]

    def test_sorting_is_uploaded_at_then_evidence_id(self):
        ordered_hashes = [
            format(1, "064x"),
            format(3, "064x"),
            format(2, "064x"),
        ]
        expected_root = "0x" + build_levels(ordered_hashes)[-1][0].hex()
        with patch(
            "app.integrity.batcher.anchor_root",
            return_value={
                "batch_id": 4,
                "transaction_hash": "0x" + "ab" * 32,
                "block_number": 12,
                "chain_id": 31337,
            },
        ) as anchor:
            result = anchor_evidence_records(self.records)

        self.assertEqual(result["root"], expected_root)
        proofs = result["evidence_proofs"]
        self.assertEqual(
            [proof["evidence_id"] for proof in proofs],
            ["evidence-a", "evidence-z", "evidence-b"],
        )
        self.assertEqual([proof["leaf_index"] for proof in proofs], [0, 1, 2])
        self.assertEqual(
            [proof["leaf_hash"] for proof in proofs],
            [leaf_hash(value).hex() for value in ordered_hashes],
        )
        anchor.assert_called_once_with(expected_root, 3)

    def test_duplicate_evidence_id_rejected_before_anchor(self):
        duplicated = self.records + [dict(self.records[0])]
        with patch("app.integrity.batcher.anchor_root") as anchor:
            with self.assertRaisesRegex(ValueError, "unique"):
                anchor_evidence_records(duplicated)
        anchor.assert_not_called()

    def test_size_threshold_triggers(self):
        candidates = self.records * (
            DEFAULT_ANCHOR_BATCH_SIZE // len(self.records) + 1
        )
        self.assertTrue(
            should_trigger_batch(
                candidates,
                now=self.start,
                batch_size=DEFAULT_ANCHOR_BATCH_SIZE,
            )
        )

    def test_oldest_wait_threshold_triggers_at_interval(self):
        candidate = [self.records[0]]
        self.assertFalse(
            should_trigger_batch(
                candidate,
                now=self.start + timedelta(
                    seconds=DEFAULT_ANCHOR_INTERVAL_SECONDS + 4
                ),
            )
        )
        self.assertTrue(
            should_trigger_batch(
                candidate,
                now=self.start + timedelta(
                    seconds=DEFAULT_ANCHOR_INTERVAL_SECONDS + 5
                ),
            )
        )

    def test_empty_candidates_do_not_trigger(self):
        self.assertFalse(should_trigger_batch([], now=self.start))

    def test_retry_schedule_is_three_delays_then_stop(self):
        self.assertEqual(
            [retry_delay_after_failure(n) for n in (1, 2, 3)],
            [5, 15, 45],
        )
        self.assertIsNone(retry_delay_after_failure(4))

    def test_invalid_retry_number_rejected(self):
        with self.assertRaises(ValueError):
            retry_delay_after_failure(0)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.hashes = [format(number, "064x") for number in range(1, 5)]
        levels = build_levels(self.hashes)
        self.root = "0x" + levels[-1][0].hex()
        self.proof = get_proof(levels, 0)

    def verify(self, **overrides):
        values = {
            "expected_hash": self.hashes[0],
            "recomputed_hash": self.hashes[0],
            "proof": self.proof,
            "chain_batch_id": 7,
            "stored_batch_root": self.root,
        }
        values.update(overrides)
        with patch(
            "app.integrity.verify.get_batch",
            return_value={"root": self.root, "leaf_count": 4, "anchored_at": 1},
        ) as get_batch_call:
            result = verify_integrity(**values)
        return result, get_batch_call

    def test_missing_proof_is_pending_without_chain_call(self):
        result, get_batch_call = self.verify(proof=None)
        self.assertEqual(result["result"], "pending")
        get_batch_call.assert_not_called()

    def test_missing_file_or_hash_is_error(self):
        result, get_batch_call = self.verify(recomputed_hash=None)
        self.assertEqual(result["result"], "error")
        get_batch_call.assert_not_called()

    def test_changed_file_hash_is_altered(self):
        result, get_batch_call = self.verify(recomputed_hash=format(99, "064x"))
        self.assertEqual(result["result"], "altered")
        get_batch_call.assert_not_called()

    def test_tampered_stored_hash_and_file_still_fail_proof(self):
        modified = format(99, "064x")
        result, get_batch_call = self.verify(
            expected_hash=modified,
            recomputed_hash=modified,
        )
        self.assertEqual(result["result"], "altered")
        get_batch_call.assert_not_called()

    def test_modified_proof_is_altered(self):
        modified_proof = [dict(step) for step in self.proof]
        modified_proof[0]["hash"] = format(99, "064x")
        result, get_batch_call = self.verify(proof=modified_proof)
        self.assertEqual(result["result"], "altered")
        get_batch_call.assert_not_called()

    def test_stored_batch_root_mismatch_is_altered(self):
        result, get_batch_call = self.verify(stored_batch_root="0x" + "00" * 32)
        self.assertEqual(result["result"], "altered")
        get_batch_call.assert_not_called()

    def test_different_onchain_batch_root_is_altered(self):
        with patch(
            "app.integrity.verify.get_batch",
            return_value={"root": "0x" + "00" * 32, "leaf_count": 4, "anchored_at": 1},
        ):
            result = verify_integrity(
                self.hashes[0],
                self.hashes[0],
                self.proof,
                8,
                self.root,
            )
        self.assertEqual(result["result"], "altered")

    def test_chain_unavailable_is_error(self):
        with patch(
            "app.integrity.verify.get_batch",
            side_effect=ChainError("offline"),
        ):
            result = verify_integrity(
                self.hashes[0],
                self.hashes[0],
                self.proof,
                7,
                self.root,
            )
        self.assertEqual(result["result"], "error")

    def test_clean_file_and_proof_are_verified(self):
        result, _ = self.verify()
        self.assertEqual(result["result"], "verified")
        self.assertEqual(result["computed_root"], self.root)
        self.assertEqual(result["onchain_root"], self.root)


if __name__ == "__main__":
    unittest.main()
