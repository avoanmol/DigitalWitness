import unittest

from backend.app.ai.extract import extract_entities, detect_language
from backend.app.ai.normalise import normalise_entity


class AIExtractionTests(unittest.TestCase):
    def test_extracts_normalized_email_and_indian_phone(self):
        entities = extract_entities(
            "Contact: Example.User@Example.TEST; call +91 98765 43210"
        )
        found = {(item.type, item.normalised_value) for item in entities}

        self.assertIn(("email", "example.user@example.test"), found)
        self.assertIn(("phone", "+919876543210"), found)

    def test_deduplicates_repeated_entity_values(self):
        entities = extract_entities(
            "a@sample.test and A@SAMPLE.TEST"
        )

        self.assertEqual(
            [(item.type, item.normalised_value) for item in entities],
            [("email", "a@sample.test")],
        )

    def test_handle_excludes_sentence_punctuation(self):
        entities = extract_entities("Contact @sample_case_01.")

        self.assertEqual(
            [(item.type, item.normalised_value) for item in entities],
            [("handle", "sample_case_01")],
        )

    def test_phone_formats_normalize_to_the_same_value(self):
        self.assertEqual(
            normalise_entity("phone", "098765 43210"),
            normalise_entity("phone", "+91 98765 43210"),
        )

    def test_language_detector_handles_supported_scripts(self):
        self.assertEqual(detect_language("यह एक हिन्दी संदेश है।"), "hi")
        self.assertEqual(detect_language("ಇದು ಕನ್ನಡ ಸಂದೇಶವಾಗಿದೆ."), "kn")


if __name__ == "__main__":
    unittest.main()
