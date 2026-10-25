from pathlib import Path


def extract_text_from_txt(file_path: str | Path) -> str:
    """Extract text from a plain text or chat-export file."""
    path = Path(file_path)

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract text from a PDF using pdfplumber."""
    import pdfplumber

    path = Path(file_path)

    pages: list[str] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

    return "\n".join(pages)


def extract_text(file_path: str | Path) -> str:
    """Extract text based on the evidence file extension."""
    path = Path(file_path)

    suffix = path.suffix.lower()

    if suffix in {".txt", ".text", ".chat"}:
        return extract_text_from_txt(path)

    if suffix == ".pdf":
        return extract_text_from_pdf(path)

    raise ValueError(f"Unsupported file type: {suffix}")