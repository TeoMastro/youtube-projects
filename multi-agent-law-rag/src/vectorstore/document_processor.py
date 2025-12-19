"""
Document processing for Greek legal PDFs with LLM-based metadata extraction.
"""

import re
import json
from pathlib import Path
from typing import List, Dict
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI

from ..config import settings, get_text_splitter_separators
from ..utils.pdf_extractor import extract_text_from_pdf
from ..utils.text_cleaner import clean_text_for_legal_docs


def extract_fek_metadata(pdf_text: str, filename: str = "", debug: bool = False) -> Dict[str, any]:
    """
    Extract ΦΕΚ metadata using LLM.

    Args:
        pdf_text: Full text extracted from PDF
        filename: PDF filename

    Returns:
        dict: Extracted metadata
    """
    # Default metadata
    metadata = {
        'fek_number': 'Unknown',
        'publication_date': None,
        'doc_type': 'Unknown',
        'authority': 'Unknown',
        'subject': 'Unknown'
    }

    # Extract from filename as fallback
    if filename:
        file_match = re.search(r'(\d+)([ΑΒΓΔαβγδABCD])?', filename)
        if file_match:
            num = file_match.group(1)
            series = file_match.group(2) if file_match.group(2) else 'Α'
            metadata['fek_number'] = f"{num}/{series}"

    # Process first 1000 characters from first page for better date extraction
    text_sample = pdf_text[:1000] if pdf_text else ""

    if not text_sample:
        return metadata

    if debug:
        print("=" * 80)
        print(f"DEBUG: Processing file: {filename}")
        print("=" * 80)
        print(f"First 1000 characters being sent to LLM:")
        print("-" * 80)
        print(text_sample)
        print("-" * 80)
        print()

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
            max_tokens=300
        )

        # More specific Greek prompt focusing on dates at top of first page
        prompt = f"""Ανέλυσε αυτό το ΦΕΚ έγγραφο. Η ΗΜΕΡΟΜΗΝΙΑ είναι πάντα στην κορυφή της πρώτης σελίδας.

Επιστρέψε JSON:
{{
  "publication_date": "YYYY-MM-DD",
  "doc_type": "Νόμος ή Απόφαση ή Διάταγμα",
  "fek_number": "αριθμός/σειρά",
  "authority": "υπουργείο",
  "subject": "θέμα"
}}

Κείμενο:
{text_sample}"""

        response = llm.invoke(prompt)

        # Parse and merge with fallback metadata
        content = response.content.strip()

        if debug:
            print(f"LLM Response:")
            print("-" * 80)
            print(content)
            print("-" * 80)
            print()

        # Handle markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        llm_data = json.loads(content)
        for key, value in llm_data.items():
            if value and value != "null" and value != "":
                metadata[key] = value

        if debug:
            print(f"Extracted Metadata:")
            print("-" * 80)
            print(json.dumps(metadata, indent=2, ensure_ascii=False))
            print("=" * 80)
            print()

    except Exception as e:
        # If LLM fails, keep fallback metadata (filename-based)
        if debug:
            print(f"ERROR: {e}")
            print("=" * 80)
        pass

    return metadata


def process_pdf_to_chunks(
    pdf_path: str | Path,
    clean_text: bool = True,
    extract_metadata: bool = True
) -> List[Document]:
    """
    Process PDF into chunks with LLM-extracted metadata.

    Args:
        pdf_path: Path to PDF file
        clean_text: Whether to clean/normalize text
        extract_metadata: Whether to extract ΦΕΚ metadata using LLM

    Returns:
        List[Document]: Chunked documents with metadata
    """
    pdf_path = Path(pdf_path)

    # Extract text
    full_text = extract_text_from_pdf(pdf_path)

    if not full_text or len(full_text.strip()) < 50:
        return []

    # Clean text if requested
    if clean_text:
        full_text = clean_text_for_legal_docs(full_text)

    # Extract metadata using LLM
    doc_metadata = {}
    if extract_metadata:
        doc_metadata = extract_fek_metadata(full_text, pdf_path.name)

    # Add source info
    doc_metadata['source'] = pdf_path.name
    doc_metadata['source_path'] = str(pdf_path.absolute())

    # Create text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        separators=get_text_splitter_separators(),
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )

    # Split into chunks
    chunks = text_splitter.split_text(full_text)

    # Create Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        chunk_metadata = doc_metadata.copy()
        chunk_metadata['chunk_index'] = i
        chunk_metadata['total_chunks'] = len(chunks)

        doc = Document(
            page_content=chunk,
            metadata=chunk_metadata
        )
        documents.append(doc)

    return documents
