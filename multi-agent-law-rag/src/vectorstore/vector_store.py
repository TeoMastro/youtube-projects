"""
FAISS vector store with hybrid search (semantic + BM25).
"""

from typing import List, Dict, Optional
import pickle
from pathlib import Path
import tiktoken
from langchain_community.vectorstores import FAISS
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.schema import Document

from ..config import settings, get_vectorstore_path
from .embeddings import get_embedding_model

# Initialize tiktoken encoding for accurate token counting
try:
    _encoding = tiktoken.get_encoding("cl100k_base")
except:
    _encoding = None


def estimate_token_count(text: str) -> int:
    """
    Accurately count tokens for text using tiktoken.
    Falls back to approximation if tiktoken unavailable.

    Args:
        text: Input text

    Returns:
        int: Accurate token count
    """
    if _encoding is not None:
        return len(_encoding.encode(text))
    else:
        # Fallback: conservative estimate for Greek text
        return len(text) // 2


def get_faiss_index_path():
    """Get the path to the FAISS index file."""
    vectorstore_path = get_vectorstore_path()
    return vectorstore_path / "faiss_index"


def get_or_create_collection(embeddings=None):
    """
    Get or create FAISS vectorstore with Greek settings.

    Returns:
        FAISS: LangChain FAISS vectorstore instance
    """
    if embeddings is None:
        embeddings = get_embedding_model()

    index_path = get_faiss_index_path()

    # Try to load existing index
    if index_path.exists():
        try:
            vectorstore = FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            return vectorstore
        except:
            pass

    # Create new empty vectorstore
    # We'll need to add documents before it's usable
    return None


def add_documents(documents: List[Document], vectorstore=None):
    """
    Add documents to FAISS with batch insertion based on token limits.
    Pre-computes embeddings in batches to stay under OpenAI's 300k token limit.

    Args:
        documents: List of Document objects
        vectorstore: FAISS instance (creates new if None)

    Returns:
        FAISS: Updated vectorstore
    """
    if not documents:
        return vectorstore

    embeddings = get_embedding_model()
    index_path = get_faiss_index_path()

    if vectorstore is None:
        vectorstore = get_or_create_collection(embeddings)

    # Batch documents by token count to avoid OpenAI API limits
    # Using configurable token limit per batch (default 250k, API limit is 300k)
    MAX_TOKENS_PER_BATCH = settings.MAX_TOKENS_PER_EMBEDDING_BATCH

    batches = []
    current_batch = []
    current_token_count = 0

    for doc in documents:
        doc_tokens = estimate_token_count(doc.page_content)

        # If adding this doc would exceed limit, start new batch
        if current_token_count + doc_tokens > MAX_TOKENS_PER_BATCH and current_batch:
            batches.append(current_batch)
            current_batch = [doc]
            current_token_count = doc_tokens
        else:
            current_batch.append(doc)
            current_token_count += doc_tokens

    # Add remaining documents
    if current_batch:
        batches.append(current_batch)

    print(f"Processing {len(documents)} chunks in {len(batches)} batch(es)")

    # Process each batch - pre-compute embeddings to control batch size
    for i, batch in enumerate(batches, 1):
        batch_tokens = sum(estimate_token_count(doc.page_content) for doc in batch)
        print(f"  Batch {i}/{len(batches)}: {len(batch)} chunks (~{batch_tokens:,} tokens)")

        # Extract texts for embedding
        texts = [doc.page_content for doc in batch]

        # Generate embeddings for this batch
        batch_embeddings = embeddings.embed_documents(texts)

        # Create text-embedding pairs
        text_embeddings = list(zip(texts, batch_embeddings))

        # If no existing vectorstore, create from first batch
        if vectorstore is None:
            # Create FAISS index from pre-computed embeddings
            vectorstore = FAISS.from_embeddings(
                text_embeddings=text_embeddings,
                embedding=embeddings,
                metadatas=[doc.metadata for doc in batch]
            )
        else:
            # Add pre-computed embeddings to existing vectorstore
            vectorstore.add_embeddings(
                text_embeddings=text_embeddings,
                metadatas=[doc.metadata for doc in batch]
            )

    # Save the index
    vectorstore.save_local(str(index_path))
    print(f"Successfully added all documents to vector store")

    return vectorstore


def similarity_search(
    query: str,
    vectorstore=None,
    k: int = None,
    filters: Dict = None
) -> List[Document]:
    """
    Search for similar documents with optional metadata filtering.

    Args:
        query: Query text
        vectorstore: FAISS instance (creates new if None)
        k: Number of results (uses config if None)
        filters: Metadata filters (e.g., {"publication_date": {"$gte": "2020-01-01"}})

    Returns:
        List[Document]: Retrieved documents
    """
    if vectorstore is None:
        vectorstore = get_or_create_collection()

    if vectorstore is None:
        return []

    if k is None:
        k = settings.RETRIEVAL_TOP_K

    # FAISS doesn't support filters natively, so we filter after retrieval
    results = vectorstore.similarity_search(query, k=k*2 if filters else k)

    # Apply metadata filters manually if provided
    if filters:
        filtered_results = []
        for doc in results:
            if _matches_filter(doc.metadata, filters):
                filtered_results.append(doc)
                if len(filtered_results) >= k:
                    break
        return filtered_results

    return results[:k]


def _matches_filter(metadata: Dict, filters: Dict) -> bool:
    """Check if metadata matches the filter criteria."""
    for key, condition in filters.items():
        if key not in metadata:
            return False

        value = metadata[key]

        # Handle different filter operators
        if isinstance(condition, dict):
            for op, target in condition.items():
                if op == "$gte" and value < target:
                    return False
                elif op == "$lte" and value > target:
                    return False
                elif op == "$eq" and value != target:
                    return False
        else:
            # Direct equality
            if value != condition:
                return False

    return True


def get_hybrid_retriever(vectorstore=None, documents: List[Document] = None, k: int = 5):
    """
    Create hybrid retriever combining semantic (vector) and keyword (BM25) search.

    Semantic: Good for conceptual queries ("νόμοι για εργασία")
    BM25: Good for exact legal terms ("άρθρο 10", "ΦΕΚ 123/Α/2024")

    Args:
        vectorstore: FAISS instance
        documents: List of documents for BM25 (if None, retrieved from vectorstore)
        k: Number of results per retriever

    Returns:
        EnsembleRetriever: Combined retriever
    """
    if vectorstore is None:
        vectorstore = get_or_create_collection()

    if vectorstore is None:
        # If no vectorstore exists yet, return None
        return None

    # Semantic retriever from FAISS
    semantic_retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )

    # BM25 keyword retriever
    # If documents not provided, get all from vectorstore
    if documents is None:
        # Get documents from FAISS docstore
        documents = list(vectorstore.docstore._dict.values())

    if not documents:
        # If no documents, return just semantic retriever
        return semantic_retriever

    bm25_retriever = BM25Retriever.from_documents(documents, k=k)

    # Ensemble with configurable weights
    hybrid_retriever = EnsembleRetriever(
        retrievers=[semantic_retriever, bm25_retriever],
        weights=[settings.SEMANTIC_WEIGHT, settings.BM25_WEIGHT]
    )

    return hybrid_retriever


def delete_collection(vectorstore=None):
    """Delete the entire FAISS index."""
    index_path = get_faiss_index_path()

    if index_path.exists():
        import shutil
        try:
            shutil.rmtree(index_path)
        except:
            pass


def get_collection_stats(vectorstore=None) -> Dict[str, any]:
    """
    Get collection statistics.

    Returns:
        dict: Statistics including document count, date range, types
    """
    if vectorstore is None:
        vectorstore = get_or_create_collection()

    if vectorstore is None:
        return {
            "total_documents": 0,
            "document_types": [],
            "authorities": [],
            "date_range": {"earliest": None, "latest": None},
        }

    try:
        # Get all documents from FAISS docstore
        documents = list(vectorstore.docstore._dict.values())
        count = len(documents)

        if count > 0:
            # Extract unique document types
            doc_types = set()
            authorities = set()
            dates = []

            for doc in documents:
                meta = doc.metadata
                if meta.get("doc_type"):
                    doc_types.add(meta["doc_type"])
                if meta.get("authority"):
                    authorities.add(meta["authority"])
                if meta.get("publication_date"):
                    dates.append(meta["publication_date"])

            stats = {
                "total_documents": count,
                "document_types": list(doc_types),
                "authorities": list(authorities),
                "date_range": {
                    "earliest": min(dates) if dates else None,
                    "latest": max(dates) if dates else None,
                },
            }
        else:
            stats = {
                "total_documents": 0,
                "document_types": [],
                "authorities": [],
                "date_range": {"earliest": None, "latest": None},
            }

        return stats

    except Exception as e:
        return {
            "total_documents": 0,
            "error": str(e)
        }


def check_if_document_exists(source_name: str, vectorstore=None) -> bool:
    """
    Check if a document with given source name already exists.

    Args:
        source_name: Document source name (filename)
        vectorstore: FAISS instance

    Returns:
        bool: True if document exists
    """
    if vectorstore is None:
        vectorstore = get_or_create_collection()

    if vectorstore is None:
        return False

    try:
        # Check all documents in docstore
        documents = list(vectorstore.docstore._dict.values())
        for doc in documents:
            if doc.metadata.get("source") == source_name:
                return True
        return False
    except:
        return False
