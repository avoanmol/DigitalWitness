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
    anchor_persisted_evidence_records,
    retry_delay_after_failure,
    should_trigger_batch,
)
from app.integrity.chain import ChainError
from app.integrity.merkle import build_levels, get_proof, leaf_hash
from app.integrity.service import inspect_stored_evidence
from app.integrity.verify import verify_integrity


class BatcherTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
        self.records = [
            {
                "id": "evidence-b",
                "uploaded_at": self.start + timedelta(seconds=5),
                "status": "stored",
                "sha256": format(2, "064x"),
            },
            {
                "id": "evidence-z",
                "uploaded_at": self.start,
                "status": "stored",
                "sha256": format(3, "064x"),
            },
            {
                "id": "evidence-a",
                "uploaded_at": self.start,
                "status": "stored",
                "sha256": format(1, "064x"),
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
                "chain_batch_id": 4,
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

    def test_non_stored_evidence_rejected_before_anchor(self):
        received = [dict(self.records[0], status="received")]
        with patch("app.integrity.batcher.anchor_root") as anchor:
            with self.assertRaisesRegex(ValueError, "status 'stored'"):
                anchor_evidence_records(received)
        anchor.assert_not_called()

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

    def test_anchor_on_another_chain_is_error_not_altered(self):
        from types import SimpleNamespace

        evidence = SimpleNamespace(
            sha256="1" * 64,
            storage_key="private/object-key",
            status="anchored",
        )
        proof = SimpleNamespace(proof=[], leaf_hash="0" * 64, leaf_index=0)
        batch = SimpleNamespace(
            status="confirmed",
            chain_batch_id=1,
            tx_hash="0x" + "ab" * 32,
            block_number=10,
            chain_id=31337,
            root_hash="0x" + "cd" * 32,
            leaf_count=1,
        )
        with patch("app.integrity.service.get_chain_id", return_value=80002), patch(
            "app.integrity.service.get_encrypted_evidence"
        ) as storage_read:
            result = inspect_stored_evidence(evidence, proof, batch)

        self.assertEqual(result["result"], "error")
        self.assertIn("recorded on chain 31337", result["reason"])
        self.assertNotEqual(result["result"], "altered")
        storage_read.assert_not_called()


class PersistedBatchServiceTests(unittest.TestCase):
    def setUp(self):
        self.batch_id = "batch-1"
        self.records = [
            {
                "id": "evidence-1",
                "uploaded_at": datetime(2026, 10, 20, tzinfo=timezone.utc),
                "status": "stored",
                "sha256": format(1, "064x"),
            },
            {
                "id": "evidence-2",
                "uploaded_at": datetime(2026, 10, 20, 0, 0, 1, tzinfo=timezone.utc),
                "status": "stored",
                "sha256": format(2, "064x"),
            },
        ]
        self.states = {"batch": None, "evidence": ["stored", "stored"]}
        self.events = []

    class Session:
        def __init__(self, events):
            self.events = events

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def commit(self):
            self.events.append("commit")

    def factory(self):
        return self.Session(self.events)

    def test_success_persists_each_state_in_order(self):
        from types import SimpleNamespace

        def create_building(session, **kwargs):
            self.assertEqual(self.states["batch"], None)
            self.assertEqual(len(kwargs["evidence_proofs"]), 2)
            self.states["batch"] = "building"
            self.events.append("building")
            return SimpleNamespace(id=self.batch_id)

        def mark_submitted(session, **kwargs):
            self.assertEqual(self.states["batch"], "building")
            self.states["batch"] = "submitted"
            self.events.append("submitted")

        def confirm(session, **kwargs):
            self.assertEqual(self.states["batch"], "submitted")
            self.states["batch"] = "confirmed"
            self.states["evidence"] = ["anchored", "anchored"]
            self.events.append("confirmed")
            return SimpleNamespace(id=self.batch_id)

        submission = {
            "transaction_hash": "0x" + "ab" * 32,
            "chain_id": 31337,
        }
        receipt = {
            **submission,
            "chain_batch_id": 5,
            "block_number": 12,
        }
        def submit(root, leaf_count):
            self.events.append("chain_submit")
            return submission

        def wait(submitted, root, leaf_count):
            self.events.append("confirmation_wait")
            return receipt

        with patch(
            "app.integrity.persistence.create_building_batch",
            side_effect=create_building,
        ), patch(
            "app.integrity.persistence.mark_batch_submitted",
            side_effect=mark_submitted,
        ) as submitted, patch(
            "app.integrity.persistence.confirm_submitted_batch",
            side_effect=confirm,
        ), patch(
            "app.integrity.persistence.mark_submitted_batch_failed"
        ) as failed, patch(
            "app.integrity.batcher.submit_root", side_effect=submit
        ) as submit_call, patch(
            "app.integrity.batcher.wait_for_anchor", side_effect=wait
        ) as wait_call:
            result = anchor_persisted_evidence_records(self.records, self.factory)

        self.assertEqual(self.states["batch"], "confirmed")
        self.assertEqual(self.states["evidence"], ["anchored", "anchored"])
        self.assertEqual(result["batch_id"], self.batch_id)
        self.assertLess(self.events.index("building"), self.events.index("chain_submit"))
        self.assertLess(self.events.index("chain_submit"), self.events.index("submitted"))
        self.assertLess(self.events.index("submitted"), self.events.index("confirmation_wait"))
        self.assertLess(self.events.index("confirmation_wait"), self.events.index("confirmed"))
        submitted.assert_called_once()
        submit_call.assert_called_once_with(result["root"], result["leaf_count"])
        wait_call.assert_called_once_with(submission, result["root"], result["leaf_count"])
        failed.assert_not_called()

    def test_chain_failure_marks_failed_and_keeps_evidence_retryable(self):
        from types import SimpleNamespace

        def create_building(session, **kwargs):
            self.states["batch"] = "building"
            self.events.append("building")
            return SimpleNamespace(id=self.batch_id)

        def mark_failed(session, **kwargs):
            self.assertIn(self.states["batch"], {"building", "submitted"})
            self.states["batch"] = "failed"
            self.events.append("failed")

        with patch(
            "app.integrity.persistence.create_building_batch",
            side_effect=create_building,
        ), patch(
            "app.integrity.persistence.mark_submitted_batch_failed",
            side_effect=mark_failed,
        ) as failed, patch(
            "app.integrity.batcher.submit_root",
            side_effect=ChainError("rpc offline"),
        ), patch(
            "app.integrity.batcher.wait_for_anchor"
        ) as wait:
            with self.assertRaisesRegex(ChainError, "offline"):
                anchor_persisted_evidence_records(self.records, self.factory)

        self.assertEqual(self.states["batch"], "failed")
        self.assertEqual(self.states["evidence"], ["stored", "stored"])
        self.assertNotIn("altered", self.states["evidence"])
        self.assertEqual(self.events[-2:], ["failed", "commit"])
        self.assertEqual(failed.call_args.kwargs["failure_code"], "submission_failed")
        wait.assert_not_called()

    def test_confirmation_timeout_retains_submitted_batch_and_proofs(self):
        from types import SimpleNamespace

        def create_building(session, **kwargs):
            self.states["batch"] = "building"
            return SimpleNamespace(id=self.batch_id)

        def mark_submitted(session, **kwargs):
            self.states["batch"] = "submitted"

        def mark_failed(session, **kwargs):
            self.states["batch"] = "failed"

        with patch(
            "app.integrity.persistence.create_building_batch",
            side_effect=create_building,
        ), patch(
            "app.integrity.persistence.mark_batch_submitted",
            side_effect=mark_submitted,
        ), patch(
            "app.integrity.persistence.mark_submitted_batch_failed",
            side_effect=mark_failed,
        ), patch(
            "app.integrity.batcher.submit_root",
            return_value={"transaction_hash": "0x" + "ab" * 32, "chain_id": 31337},
        ), patch(
            "app.integrity.batcher.wait_for_anchor",
            side_effect=ChainError("receipt timeout"),
        ):
            with self.assertRaisesRegex(ChainError, "timeout"):
                anchor_persisted_evidence_records(self.records, self.factory)

        self.assertEqual(self.states["batch"], "submitted")
        self.assertEqual(self.states["evidence"], ["stored", "stored"])
        self.assertNotIn("altered", self.states["evidence"])

    def test_non_stored_evidence_never_starts_a_batch(self):
        invalid = [dict(self.records[0], status="failed")]
        with patch("app.integrity.batcher.submit_root") as submit:
            with self.assertRaisesRegex(ValueError, "status 'stored'"):
                anchor_persisted_evidence_records(invalid, self.factory)
        submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
