import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from backend.app.api.cases import _case_summary, _display_verification


class CaseSummaryTests(unittest.TestCase):
    def setUp(self):
        self.case = SimpleNamespace(
            id=uuid4(),
            case_ref="DW-TEST-001",
            title="Synthetic case",
            description=None,
            status="open",
            created_at=datetime.now(timezone.utc),
        )

    def test_empty_case_has_no_verification_or_ai_leads(self):
        result = _case_summary(self.case, [], [])

        self.assertIsNone(result["verification"])
        self.assertEqual(result["evidence_count"], 0)
        self.assertEqual(result["pending_count"], 0)
        self.assertEqual(result["threat_count"], 0)
        self.assertIsNone(result["severity"])

    def test_pending_evidence_and_flags_are_summarized(self):
        evidence = [
            {"status": "stored", "verification": "pending"},
            {"status": "anchored", "verification": "verified"},
        ]
        flags = [
            SimpleNamespace(id=uuid4(), review_status="pending", severity="high", threat_class="threat"),
            SimpleNamespace(id=uuid4(), review_status="confirmed", severity="critical", threat_class="reviewed"),
        ]

        result = _case_summary(self.case, evidence, flags)

        self.assertEqual(result["verification"], "pending")
        self.assertEqual(result["evidence_count"], 2)
        self.assertEqual(result["pending_count"], 1)
        self.assertEqual(result["threat_count"], 1)
        self.assertEqual(result["threat_class"], "threat")
        self.assertEqual(result["severity"], "high")

    def test_altered_evidence_takes_precedence_over_pending(self):
        evidence = [
            {"status": "anchored", "verification": "pending"},
            {"status": "anchored", "verification": "altered"},
        ]

        result = _case_summary(self.case, evidence, [])

        self.assertEqual(result["verification"], "altered")

    def test_confirmed_anchor_without_a_file_check_is_not_waiting_for_anchor(self):
        self.assertEqual(_display_verification("anchored", None), "not_checked")
        self.assertEqual(_display_verification("anchored", "pending"), "not_checked")
        self.assertEqual(_display_verification("stored", None), "pending")

    def test_case_with_anchored_but_unchecked_evidence_is_not_checked(self):
        evidence = [
            {"status": "anchored", "verification": "pending"},
            {"status": "anchored", "verification": "verified"},
        ]
        result = _case_summary(self.case, evidence, [])
        self.assertEqual(result["verification"], "not_checked")
        self.assertEqual(result["pending_count"], 0)

    def test_completed_error_is_not_replaced_by_not_checked(self):
        self.assertEqual(_display_verification("anchored", "error"), "error")


if __name__ == "__main__":
    unittest.main()
