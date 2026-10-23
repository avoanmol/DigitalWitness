import unittest
from uuid import uuid4

from backend.audit import (
    AUDIT_CHAIN_LOCK_KEY,
    GENESIS_HASH,
    append_audit_event,
    verify_audit_chain,
)


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    """Minimal session double for deterministic audit-chain unit tests."""

    def __init__(self):
        self.entries = []
        self.operations = []

    def execute(self, statement, parameters):
        self.operations.append(("lock", str(statement), parameters))

    def scalar(self, _statement):
        self.operations.append(("read_latest",))
        return max(self.entries, key=lambda entry: entry.seq, default=None)

    def add(self, entry):
        entry.id = uuid4()
        self.entries.append(entry)

    def flush(self):
        for sequence, entry in enumerate(self.entries, start=1):
            entry.seq = sequence

    def scalars(self, _statement):
        return FakeScalarResult(sorted(self.entries, key=lambda entry: entry.seq))


class AuditChainTests(unittest.TestCase):
    def test_appended_entries_link_and_tampering_is_detected(self):
        db = FakeSession()
        first = append_audit_event(
            db, action="test.first", target_type="system", details={"step": 1}
        )
        second = append_audit_event(
            db, action="test.second", target_type="system", details={"step": 2}
        )

        self.assertEqual(first.prev_hash, GENESIS_HASH)
        self.assertEqual(second.prev_hash, first.entry_hash)
        self.assertTrue(verify_audit_chain(db)["valid"])

        second.details = {"step": "tampered"}
        result = verify_audit_chain(db)
        self.assertFalse(result["valid"])
        self.assertEqual(result["failed_entry_id"], str(second.id))

    def test_append_acquires_transaction_lock_before_reading_tail(self):
        db = FakeSession()
        append_audit_event(db, action="test.lock", target_type="system")

        self.assertEqual(db.operations[0][0], "lock")
        self.assertIn("pg_advisory_xact_lock", db.operations[0][1])
        self.assertEqual(db.operations[0][2], {"lock_key": AUDIT_CHAIN_LOCK_KEY})
        self.assertEqual(db.operations[1], ("read_latest",))


if __name__ == "__main__":
    unittest.main()
