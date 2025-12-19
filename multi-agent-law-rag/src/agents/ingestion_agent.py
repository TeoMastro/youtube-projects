"""
Document ingestion agent for processing PDFs into vector store.
"""

from pathlib import Path
from typing import Dict, List
from tqdm import tqdm

from .base_agent import BaseAgent
from ..config import get_documents_path
from ..vectorstore.document_processor import process_pdf_to_chunks
from ..vectorstore.vector_store import (
    get_or_create_collection,
    add_documents,
    check_if_document_exists
)


class IngestionAgent(BaseAgent):
    """Agent responsible for ingesting PDFs into vector store."""

    def __init__(self):
        super().__init__("IngestionAgent")
        self.vectorstore = None

    def execute(self, state: Dict) -> Dict:
        """Not used for ingestion - use ingest_all_documents() instead."""
        return state

    def ingest_all_documents(self, force: bool = False) -> Dict:
        """
        Ingest all PDFs from documents directory.

        Args:
            force: If True, re-ingest even if already processed

        Returns:
            dict: Ingestion report
        """
        docs_path = get_documents_path()
        pdf_files = list(docs_path.glob("*.pdf"))

        if not pdf_files:
            return {
                "status": "no_files",
                "message": f"No PDF files found in {docs_path}",
                "total_docs": 0,
                "success": 0,
                "failed": 0,
            }

        # Initialize vectorstore once
        self.vectorstore = get_or_create_collection()

        results = {
            "total_docs": len(pdf_files),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "failed_files": [],
            "total_chunks": 0,
        }

        print(f"Found {len(pdf_files)} PDF files")

        for pdf_path in tqdm(pdf_files, desc="Ingesting PDFs"):
            try:
                result = self.ingest_single_document(pdf_path, force=force)

                if result["status"] == "skipped":
                    results["skipped"] += 1
                elif result["status"] == "success":
                    results["success"] += 1
                    results["total_chunks"] += result["chunks_created"]
                else:
                    results["failed"] += 1
                    results["failed_files"].append(str(pdf_path.name))

            except Exception as e:
                results["failed"] += 1
                results["failed_files"].append(f"{pdf_path.name}: {str(e)}")

        return results

    def ingest_single_document(self, pdf_path: str | Path, force: bool = False) -> Dict:
        """
        Ingest a single PDF document.

        Args:
            pdf_path: Path to PDF file
            force: If True, re-ingest even if already processed

        Returns:
            dict: Ingestion result
        """
        pdf_path = Path(pdf_path)

        # Check if already ingested
        if not force and self.check_if_ingested(pdf_path):
            return {
                "status": "skipped",
                "message": f"{pdf_path.name} already ingested",
                "chunks_created": 0,
            }

        # Process PDF to chunks
        documents = process_pdf_to_chunks(pdf_path, clean_text=True, extract_metadata=True)

        # Add to vectorstore
        if self.vectorstore is None:
            self.vectorstore = get_or_create_collection()

        add_documents(documents, self.vectorstore)

        # Extract metadata from first document
        metadata = documents[0].metadata if documents else {}

        return {
            "status": "success",
            "message": f"Ingested {pdf_path.name}",
            "chunks_created": len(documents),
            "metadata": {
                "fek_number": metadata.get("fek_number"),
                "doc_type": metadata.get("doc_type"),
                "publication_date": metadata.get("publication_date"),
            }
        }

    def check_if_ingested(self, pdf_path: Path) -> bool:
        """
        Check if PDF is already ingested.

        Args:
            pdf_path: Path to PDF

        Returns:
            bool: True if already ingested
        """
        if self.vectorstore is None:
            self.vectorstore = get_or_create_collection()

        return check_if_document_exists(pdf_path.name, self.vectorstore)

    def get_ingestion_report(self) -> Dict:
        """Get current ingestion statistics."""
        from ..vectorstore.vector_store import get_collection_stats

        if self.vectorstore is None:
            self.vectorstore = get_or_create_collection()

        return get_collection_stats(self.vectorstore)


# Global instance
ingestion_agent = IngestionAgent()
