"""
Embedding model configuration and management for Greek text.
"""

from typing import List
from langchain_openai import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings


def get_embedding_model() -> OpenAIEmbeddings:
    """Get configured OpenAI embeddings model with Greek text support."""
    embeddings = OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    return embeddings


@retry(
    stop=stop_after_attempt(settings.MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def batch_embed_documents(
    texts: List[str],
    embeddings: OpenAIEmbeddings = None,
    batch_size: int = 100
) -> List[List[float]]:
    """Generate embeddings for multiple documents with batching and retry logic."""
    if not texts:
        return []

    if embeddings is None:
        embeddings = get_embedding_model()

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = embeddings.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


@retry(
    stop=stop_after_attempt(settings.MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def embed_query(query: str, embeddings: OpenAIEmbeddings = None) -> List[float]:
    """Generate embedding for a single query with retry logic."""
    if embeddings is None:
        embeddings = get_embedding_model()

    query_embedding = embeddings.embed_query(query)
    return query_embedding


def get_embedding_dimension(model_name: str = None) -> int:
    """Get the embedding dimension for a given model."""
    model_name = model_name or settings.OPENAI_EMBEDDING_MODEL

    dimensions = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    return dimensions.get(model_name, 1536)
