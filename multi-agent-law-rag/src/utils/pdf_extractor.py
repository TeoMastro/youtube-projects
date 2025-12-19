"""
PDF text extraction with Greek language support.
"""

from pathlib import Path
import pdfplumber

from .validators import validate_pdf_file


def extract_text_from_pdf(pdf_path: str | Path, fallback: bool = True) -> str:
    """Extract all text from a PDF file with Greek text support."""
    pdf_path = Path(pdf_path)

    # Validate PDF
    validate_pdf_file(pdf_path)

    # Try pdfplumber FIRST (captures headers better for Greek FEK documents)
    try:
        text = _extract_with_pdfplumber(pdf_path)
        if text and len(text.strip()) > 0:
            return text
    except:
        pass

    return ""


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    """Extract text using pdfplumber library."""
    text_parts = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except:
                continue

    return "\n\n".join(text_parts)


def is_text_extractable(pdf_path: str | Path) -> bool:
    """Check if PDF has extractable text."""
    try:
        text = extract_text_from_pdf(pdf_path, fallback=True)
        return len(text.strip()) >= 100
    except:
        return False
