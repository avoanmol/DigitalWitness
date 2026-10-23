from pathlib import Path

import pytest

from backend.app.ai.text_extract import (
    extract_text,
    extract_text_from_txt,
)


def test_extracts_text_file(tmp_path: Path):
    file_path = tmp_path / "chat.txt"

    file_path.write_text(
        "Hello @rahul123\nCall +91 9876543210",
        encoding="utf-8",
    )

    text = extract_text_from_txt(file_path)

    assert text == "Hello @rahul123\nCall +91 9876543210"


def test_extract_text_detects_txt_extension(tmp_path: Path):
    file_path = tmp_path / "chat.txt"

    file_path.write_text(
        "This is a chat export.",
        encoding="utf-8",
    )

    text = extract_text(file_path)

    assert text == "This is a chat export."


def test_unsupported_file_type():
    with pytest.raises(ValueError):
        extract_text("evidence.png")