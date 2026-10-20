from backend.app.ai.normalise import (
    normalize_email,
    normalize_handle,
    normalize_phone,
    normalize_text,
    normalize_url,
)


def test_normalize_text():
    assert normalize_text("  hello  ") == "hello"


def test_normalize_unicode():
    assert normalize_text("ＡＢＣ") == "ABC"


def test_normalize_phone():
    assert normalize_phone("98765 43210") == "+919876543210"
    assert normalize_phone("+91 98765 43210") == "+919876543210"


def test_normalize_email():
    assert normalize_email(" TEST@EXAMPLE.COM ") == "test@example.com"


def test_normalize_handle():
    assert normalize_handle("Rahul123") == "@rahul123"
    assert normalize_handle("@Rahul123") == "@rahul123"


def test_normalize_url():
    assert normalize_url("https://example.com/") == "https://example.com"