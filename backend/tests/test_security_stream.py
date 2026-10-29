import base64
import io
import os
import unittest
from unittest.mock import patch

from backend.security import decrypt_evidence, encrypt_evidence_stream


class EvidenceStreamEncryptionTests(unittest.TestCase):
    def test_stream_format_round_trips_through_existing_decryptor(self):
        data = (b"DigitalWitness synthetic evidence\n" * 100_000) + bytes(range(256))
        with patch.dict(os.environ, {"EVIDENCE_ENC_KEY": base64.b64encode(b"k" * 32).decode()}):
            encrypted = io.BytesIO()
            nonce = encrypt_evidence_stream(io.BytesIO(data), encrypted)
            stored = encrypted.getvalue()
            self.assertEqual(stored[:12], nonce)
            self.assertEqual(decrypt_evidence(stored[12:], nonce), data)


if __name__ == "__main__":
    unittest.main()
