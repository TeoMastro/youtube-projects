"""
Input validation utilities.
"""

import os
from pathlib import Path
from pypdf import PdfReader


def validate_pdf_file(pdf_path: str | Path) -> bool:
    """Validate that a file is a valid, readable PDF."""
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise ValueError(f"PDF file not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"File is not a PDF: {pdf_path}")

    file_size = pdf_path.stat().st_size
    if file_size == 0:
        raise ValueError(f"PDF file is empty: {pdf_path}")

    if file_size > 100 * 1024 * 1024:  # 100MB
        raise ValueError(f"PDF file too large: {pdf_path}")

    try:
        reader = PdfReader(str(pdf_path))
        if len(reader.pages) == 0:
            raise ValueError(f"PDF has no pages: {pdf_path}")
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {e}")

    return True
