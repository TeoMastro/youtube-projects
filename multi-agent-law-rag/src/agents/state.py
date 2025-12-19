"""
LangGraph state definitions for multi-agent system.
"""

from typing import TypedDict, Optional, List, Dict
from datetime import datetime
from langchain.schema import Document


class IngestionState(TypedDict):
    """State for document ingestion workflow."""
    pdf_path: str
    status: str  # "pending", "processing", "completed", "failed"
    chunks_created: int
    metadata_extracted: Dict[str, any]
    error: Optional[str]


class MultiAgentState(TypedDict):
    """
    Shared state for multi-agent Q&A workflow.
    All agents receive this state and update their specific fields.
    """
    # Input
    query: str  # User's question

    # Temporal agent fields
    extracted_date: Optional[datetime]  # Parsed date from query
    temporal_filter: Optional[Dict]  # Date range filter

    # RAG agent fields
    rag_response: str  # Response from RAG agent
    rag_sources: List[Document]  # Retrieved documents
    rag_confidence: float  # 0.0 - 1.0
    rag_source_metadata: Optional[Dict]  # Tracks if response uses RAG, pretrained, or both

    # Temporal agent fields
    temporal_response: str  # Response from Temporal agent
    temporal_sources: List[Document]  # Date-filtered documents
    temporal_confidence: float  # 0.0 - 1.0

    # Supervisor agent fields
    final_answer: str  # Supervisor's synthesized response
    confidence_score: float  # Weighted confidence
    primary_source: str  # "local" or "web"
    citations: List[Dict]  # All sources combined

    # Metadata
    timestamp: datetime  # Query timestamp
    error: Optional[str]  # Error message if any agent failed


def create_initial_state(query: str) -> MultiAgentState:
    """
    Create initial multi-agent state with default values.

    Args:
        query: User's question

    Returns:
        MultiAgentState: Initial state
    """
    return MultiAgentState(
        # Input
        query=query,

        # Temporal
        extracted_date=None,
        temporal_filter=None,

        # RAG
        rag_response="",
        rag_sources=[],
        rag_confidence=0.0,
        rag_source_metadata=None,

        # Temporal
        temporal_response="",
        temporal_sources=[],
        temporal_confidence=0.0,

        # Supervisor
        final_answer="",
        confidence_score=0.0,
        primary_source="",
        citations=[],

        # Metadata
        timestamp=datetime.now(),
        error=None,
    )
