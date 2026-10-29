import os
import unittest
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("JWT_SECRET", "unit-test-secret-with-at-least-thirty-two-bytes")

from backend.main import ALLOWED_TYPES, _file_signature_matches  # noqa: E402


class SupportedUploadTypeTests(unittest.TestCase):
    def test_every_documented_extension_is_allowed(self):
        self.assertEqual(
            ALLOWED_TYPES,
            {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".txt", ".json", ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".webm"},
        )

    def test_each_media_type_requires_its_signature(self):
        valid = {
            ".jpg": b"\xff\xd8\xffsample",
            ".jpeg": b"\xff\xd8\xffsample",
            ".png": b"\x89PNG\r\n\x1a\nsample",
            ".webp": b"RIFF\x00\x00\x00\x00WEBP",
            ".pdf": b"%PDF-1.7 sample",
            ".txt": b"plain text",
            ".json": b'{"sample":true}',
            ".mp3": b"ID3sample",
            ".wav": b"RIFF\x00\x00\x00\x00WAVE",
            ".m4a": b"\x00\x00\x00\x18ftypM4A ",
            ".mp4": b"\x00\x00\x00\x18ftypisom",
            ".mov": b"\x00\x00\x00\x18ftypqt  ",
            ".webm": b"\x1a\x45\xdf\xa3sample",
        }
        for extension, data in valid.items():
            with self.subTest(extension=extension):
                self.assertTrue(_file_signature_matches(data, extension))
        for extension, data in valid.items():
            if extension in {".txt", ".json"}:
                continue
            with self.subTest(extension=extension, invalid=True):
                self.assertFalse(_file_signature_matches(b"not-the-right-header", extension))


if __name__ == "__main__":
    unittest.main()
