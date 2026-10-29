import os
import unittest
from unittest.mock import patch

from backend.app.receipts import canonical_receipt_bytes, sign_receipt, verify_receipt


class ReceiptSignatureTests(unittest.TestCase):
    def test_canonical_serialization_ignores_dictionary_insertion_order(self):
        with patch.dict(os.environ, {"RECEIPT_HMAC_KEY": "r" * 40}):
            left = {"evidence_id": "e-1", "sha256": "abc"}
            right = {"sha256": "abc", "evidence_id": "e-1"}
            self.assertEqual(canonical_receipt_bytes(left), canonical_receipt_bytes(right))
            signature = sign_receipt(left)
            self.assertTrue(verify_receipt(right, signature))
            self.assertFalse(verify_receipt({**right, "sha256": "changed"}, signature))

    def test_short_signing_secret_fails_closed(self):
        with patch.dict(os.environ, {"RECEIPT_HMAC_KEY": "short"}):
            with self.assertRaisesRegex(RuntimeError, "at least 32 bytes"):
                sign_receipt({"receipt_id": "example"})


if __name__ == "__main__":
    unittest.main()
