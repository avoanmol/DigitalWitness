from __future__ import annotations

import io
import os
import re
import unicodedata
import warnings
from dataclasses import dataclass
from pathlib import Path
from pypdf import PdfReader
from backend.app.ai.normalise import is_common_url, normalise_entity

MAX_TEXT_CHARS = 100_000
MAX_OCR_PIXELS = 40_000_000
MAX_PDF_OCR_PAGES = 5
EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+", re.I)
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"']+")
HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9._]{2,64}")
PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{5,}\d(?!\w)")

@dataclass(frozen=True)
class ExtractedEntity:
    type: str
    raw_value: str
    normalised_value: str
    confidence: float
    start: int
    end: int


def _ocr_language() -> tuple[str, object]:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR dependencies are missing; install backend requirements.") from exc
    custom_binary = os.getenv("TESSERACT_CMD")
    if custom_binary:
        pytesseract.pytesseract.tesseract_cmd = custom_binary
    try:
        available = set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR is not installed or is not on PATH.") from exc
    requested = [item.strip() for item in os.getenv("OCR_LANGUAGES", "eng+hin+kan").split("+") if item.strip()]
    selected = [item for item in requested if item in available]
    if not selected and "eng" in available:
        selected = ["eng"]
    if not selected:
        raise RuntimeError("No configured OCR language data is installed.")
    return "+".join(selected), pytesseract


def _run_ocr(image) -> tuple[str, str]:
    language, pytesseract = _ocr_language()
    try:
        timeout = max(1, min(60, int(os.getenv("OCR_TIMEOUT_SECONDS", "25"))))
    except ValueError as exc:
        raise RuntimeError("OCR_TIMEOUT_SECONDS must be an integer.") from exc
    text = pytesseract.image_to_string(image, lang=language, config="--oem 1 --psm 6", timeout=timeout)
    return text.strip(), language


def _ocr_image(data: bytes) -> tuple[str, str]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("OCR image dependencies are missing; install backend requirements.") from exc
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("OCR supports JPEG, PNG, and WEBP images only.")
                if getattr(original, "n_frames", 1) != 1:
                    raise ValueError("Animated images are not supported for OCR.")
                if original.width * original.height > MAX_OCR_PIXELS:
                    raise ValueError("Image exceeds the safe OCR pixel limit.")
                original.load()
                image = ImageOps.exif_transpose(original).convert("RGB")
    except Image.DecompressionBombWarning as exc:
        raise ValueError("Image exceeds the safe OCR pixel limit.") from exc
    try:
        return _run_ocr(image)
    finally:
        image.close()


def _extract_pdf(data: bytes) -> tuple[str, str]:
    reader = PdfReader(io.BytesIO(data), strict=False)
    page_count = min(len(reader.pages), MAX_PDF_OCR_PAGES)
    page_text: list[str] = []
    methods: set[str] = set()
    for index, page in enumerate(reader.pages[:page_count]):
        embedded = (page.extract_text() or "").strip()
        if embedded:
            page_text.append(embedded)
            methods.add("embedded_text")
            continue
        try:
            import pymupdf
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Scanned PDF OCR dependencies are missing; install backend requirements.") from exc
        document = pymupdf.open(stream=data, filetype="pdf")
        try:
            rendered = document.load_page(index)
            rect = rendered.rect
            if rect.width * rect.height * 4 > MAX_OCR_PIXELS:
                raise ValueError(f"PDF page {index + 1} exceeds the safe OCR pixel limit.")
            pixmap = rendered.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            try:
                text, language = _run_ocr(image)
            finally:
                image.close()
        finally:
            document.close()
        if text:
            page_text.append(text)
        methods.add("tesseract_ocr:" + language)
    text = unicodedata.normalize("NFC", "\n".join(page_text)).replace("\x00", "")[:MAX_TEXT_CHARS]
    if not text.strip():
        return "", "no_text"
    if methods == {"embedded_text"}:
        method = "embedded_text"
    elif "embedded_text" in methods:
        method = "mixed_pdf_text_ocr"
    else:
        method = next(iter(methods), "no_text")
    return text, method


def extract_document_text(data: bytes, filename: str, mime_type: str) -> tuple[str, str | None]:
    """Extract a bounded text layer from evidence, using Tesseract for image/scanned PDF pages."""
    mime_type = mime_type.split(";")[0].strip().lower()
    suffix = Path(filename).suffix.lower()
    if mime_type == "application/pdf" or suffix == ".pdf":
        return _extract_pdf(data)
    if mime_type in {"image/jpeg", "image/png", "image/webp"} or suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        text, language = _ocr_image(data)
        text = unicodedata.normalize("NFC", text).replace("\x00", "")[:MAX_TEXT_CHARS]
        return text, f"tesseract_ocr:{language}" if text.strip() else "no_text"
    if mime_type.startswith("text/") or suffix in {".txt", ".text", ".json"}:
        text = data.decode("utf-8", errors="replace")
        return unicodedata.normalize("NFC", text).replace("\x00", "")[:MAX_TEXT_CHARS], "embedded_text"
    return "", "unsupported_type"


def extract_entities(text: str) -> list[ExtractedEntity]:
    candidates: list[tuple[int, int, str, str, float]] = []
    for entity_type, pattern, confidence in (("email", EMAIL_RE, .96), ("url", URL_RE, .94), ("phone", PHONE_RE, .78), ("handle", HANDLE_RE, .90)):
        for match in pattern.finditer(text):
            raw = match.group(0)
            if entity_type in {"url", "handle"}:
                raw = raw.rstrip(".,;:!?)]}")
            start, end = match.start(), match.start() + len(raw)
            if raw and not (entity_type == "url" and is_common_url(raw)) and normalise_entity(entity_type, raw):
                candidates.append((start, end, entity_type, raw, confidence))
    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    accepted, seen, occupied = [], set(), []
    for start, end, entity_type, raw, confidence in candidates:
        if any(start < right and end > left for left, right in occupied):
            continue
        normalized = normalise_entity(entity_type, raw)
        if not normalized or (entity_type, normalized) in seen:
            continue
        seen.add((entity_type, normalized)); occupied.append((start, end))
        accepted.append(ExtractedEntity(entity_type, raw, normalized, confidence, start, end))
    return accepted


def detect_language(text: str) -> str:
    devanagari = sum("\u0900" <= char <= "\u097f" for char in text)
    kannada = sum("\u0c80" <= char <= "\u0cff" for char in text)
    if devanagari > 3 and devanagari >= kannada:
        return "hi"
    return "kn" if kannada > 3 else "en"
