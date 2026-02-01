"""
PDF text extraction with Greek language support and OCR fallback.
"""

from pathlib import Path
import pdfplumber
import re
import logging
from typing import Optional

from .validators import validate_pdf_file
from ..config import settings

# Optional imports for advanced PDF extraction
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Optional imports for OCR (cloud-based via OpenAI Vision API)
try:
    from pdf2image import convert_from_path
    import io
    import base64
    from openai import OpenAI
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path, fallback: bool = True) -> str:
    """
    Extract all text from a PDF file with Greek text support.

    Multi-layer extraction strategy:
    1. Try pdfplumber (best for standard PDFs)
    2. Try PyMuPDF if available (better font handling)
    3. Check for CID codes (indicates font encoding issues)
    4. Fall back to OCR if enabled and needed

    Args:
        pdf_path: Path to PDF file
        fallback: Whether to try fallback methods if initial extraction fails

    Returns:
        Extracted text string
    """
    pdf_path = Path(pdf_path)
    validate_pdf_file(pdf_path)

    # Method 1: Try pdfplumber FIRST (captures headers better for Greek FEK documents)
    try:
        text = _extract_with_pdfplumber(pdf_path)
        if _is_valid_text(text):
            logger.debug(f"Extracted text from {pdf_path.name} using pdfplumber")
            return text
    except Exception as e:
        logger.debug(f"pdfplumber failed for {pdf_path.name}: {e}")

    if not fallback:
        return ""

    # Method 2: Try PyMuPDF (better with some font encodings)
    if PYMUPDF_AVAILABLE:
        try:
            text = _extract_with_pymupdf(pdf_path)
            if _is_valid_text(text):
                logger.info(f"Extracted text from {pdf_path.name} using PyMuPDF (pdfplumber failed)")
                return text
        except Exception as e:
            logger.debug(f"PyMuPDF failed for {pdf_path.name}: {e}")

    # Method 3: OCR fallback for scanned documents or CID issues
    if settings.ENABLE_OCR and OCR_AVAILABLE:
        try:
            logger.info(f"Attempting OCR extraction for {pdf_path.name}")
            text = _extract_with_ocr(pdf_path)
            if _is_valid_text(text):
                logger.info(f"Successfully extracted text from {pdf_path.name} using OCR")
                return text
        except Exception as e:
            logger.warning(f"OCR failed for {pdf_path.name}: {e}")

    logger.warning(f"All extraction methods failed for {pdf_path.name}")
    return ""


def _is_valid_text(text: Optional[str], min_length: int = 100) -> bool:
    """
    Check if extracted text is valid and usable.

    Args:
        text: Extracted text to validate
        min_length: Minimum text length to consider valid

    Returns:
        True if text is valid, False otherwise
    """
    if not text or len(text.strip()) < min_length:
        return False

    # Check for excessive CID codes (indicates font encoding issues)
    # If more than 30% of the text is CID codes, it's not valid
    cid_pattern = r'\(cid:\d+\)'
    cid_matches = re.findall(cid_pattern, text)
    cid_ratio = len(''.join(cid_matches)) / len(text) if text else 0

    if cid_ratio > 0.3:
        logger.debug(f"Text contains {cid_ratio:.1%} CID codes, treating as invalid")
        return False

    return True


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


def _extract_with_pymupdf(pdf_path: Path) -> str:
    """
    Extract text using PyMuPDF (fitz) library.
    Often better at handling non-standard font encodings.
    """
    if not PYMUPDF_AVAILABLE:
        return ""

    text_parts = []
    doc = fitz.open(str(pdf_path))

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text:
                text_parts.append(page_text)
    finally:
        doc.close()

    return "\n\n".join(text_parts)


def _extract_with_ocr(pdf_path: Path) -> str:
    """
    Extract text using cloud-based OCR via OpenAI Vision API.
    Used as fallback for scanned PDFs or documents with font encoding issues (CID codes).

    Benefits:
    - No local installation required (uses OpenAI API)
    - Excellent Greek text recognition
    - Works with your existing OpenAI API key

    Returns:
        Extracted text from all pages
    """
    if not OCR_AVAILABLE:
        logger.warning("OCR requested but required packages (pdf2image, Pillow, openai) not available")
        return ""

    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return ""

    # Convert PDF to images
    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=settings.OCR_DPI,
            fmt='png'
        )
        logger.info(f"Converted {pdf_path.name} to {len(images)} images for OCR")
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        return ""

    # OCR each page using OpenAI Vision API
    text_parts = []
    for i, image in enumerate(images):
        try:
            # Convert PIL Image to base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # Call OpenAI Vision API for text extraction
            response = client.chat.completions.create(
                model=settings.OCR_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image. This is a Greek legal document (ΦΕΚ). "
                                        "Return ONLY the extracted text, preserving the original structure and formatting. "
                                        "Include all Greek and English text. Do not add any commentary or explanations."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0
            )

            page_text = response.choices[0].message.content
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())
                logger.debug(f"OCR extracted {len(page_text)} chars from page {i+1}/{len(images)}")

        except Exception as e:
            logger.warning(f"OCR failed for page {i+1}/{len(images)}: {e}")
            continue

    extracted_text = "\n\n".join(text_parts)
    logger.info(f"OCR completed for {pdf_path.name}: extracted {len(extracted_text)} total characters from {len(text_parts)} pages")
    return extracted_text


def is_text_extractable(pdf_path: str | Path) -> bool:
    """
    Check if PDF has extractable text (using all available methods).

    Returns:
        True if text can be extracted, False otherwise
    """
    try:
        text = extract_text_from_pdf(pdf_path, fallback=True)
        return _is_valid_text(text)
    except Exception as e:
        logger.debug(f"Text extraction check failed for {pdf_path}: {e}")
        return False
