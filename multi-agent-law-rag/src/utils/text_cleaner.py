"""
Greek text normalization and cleaning utilities.
"""

import re
import unicodedata


def normalize_greek_text(text: str) -> str:
    """Normalize Greek text using Unicode NFC normalization."""
    if not text:
        return text
    return unicodedata.normalize("NFC", text)


def remove_extra_whitespace(text: str) -> str:
    """Remove extra whitespace while preserving paragraph structure."""
    if not text:
        return text

    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def preserve_legal_structure(text: str) -> str:
    """Preserve legal document structure markers."""
    if not text:
        return text

    text = re.sub(r'(?<!\n\n)(Άρθρο\s+\d+)', r'\n\n\1', text)
    text = re.sub(r'(?<!\n)(Παράγραφος\s+\d+)', r'\n\1', text)
    text = re.sub(r'(?<!\n)(\d+\.)\s+', r'\n\1 ', text)
    text = re.sub(r'(?<!\n)([α-ω]\.)\s+', r'\n\1 ', text)

    return text


def handle_accents(text: str, remove: bool = False) -> str:
    """Handle Greek accents and diacritics."""
    if not text:
        return text

    if remove:
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = unicodedata.normalize("NFC", text)
    else:
        text = unicodedata.normalize("NFC", text)

    return text


def remove_control_characters(text: str) -> str:
    """Remove control characters and non-printable characters."""
    if not text:
        return text

    text = "".join(char for char in text if char in ('\n', '\t') or unicodedata.category(char)[0] != "C")
    return text


def clean_pdf_artifacts(text: str) -> str:
    """Remove common PDF extraction artifacts."""
    if not text:
        return text

    text = text.replace('\f', '\n')
    text = text.replace('\u00ad', '')
    text = text.replace('\u200b', '')

    return text


def clean_text_for_legal_docs(text: str, preserve_structure: bool = True) -> str:
    """Full cleaning pipeline for Greek legal documents."""
    if not text:
        return text

    text = remove_control_characters(text)
    text = clean_pdf_artifacts(text)
    text = normalize_greek_text(text)

    if preserve_structure:
        text = preserve_legal_structure(text)

    text = remove_extra_whitespace(text)

    return text


def normalize_for_search(text: str) -> str:
    """Normalize text for search/matching purposes."""
    if not text:
        return text

    text = handle_accents(text, remove=True)
    text = text.lower()
    text = remove_extra_whitespace(text)

    return text
