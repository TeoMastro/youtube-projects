"""
Configuration management for the Greek Legal Document RAG system.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")

    # Application Configuration
    APP_NAME: str = Field(default="Greek Legal Document RAG", env="APP_NAME")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Paths
    DOCUMENTS_DIR: str = Field(default="documents", env="DOCUMENTS_DIR")
    VECTORSTORE_DIR: str = Field(default="vectorstore", env="VECTORSTORE_DIR")
    LOGS_DIR: str = Field(default="logs", env="LOGS_DIR")

    # Vector Store Configuration
    VECTORSTORE_NAME: str = Field(default="greek_legal_docs", env="VECTORSTORE_NAME")
    VECTORSTORE_PERSIST_DIRECTORY: str = Field(default="vectorstore", env="VECTORSTORE_PERSIST_DIRECTORY")

    # Document Processing
    CHUNK_SIZE: int = Field(default=1000, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=200, env="CHUNK_OVERLAP")
    MAX_CHUNKS_PER_PDF: int = Field(default=1000, env="MAX_CHUNKS_PER_PDF")
    MAX_TOKENS_PER_EMBEDDING_BATCH: int = Field(default=250000, env="MAX_TOKENS_PER_EMBEDDING_BATCH")

    # Retrieval Configuration
    RETRIEVAL_TOP_K: int = Field(default=5, env="RETRIEVAL_TOP_K")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")

    # Hybrid Search Configuration
    SEMANTIC_WEIGHT: float = Field(default=0.5, env="SEMANTIC_WEIGHT")
    BM25_WEIGHT: float = Field(default=0.5, env="BM25_WEIGHT")

    # Multi-Agent Configuration
    ENABLE_RAG_AGENT: bool = Field(default=True, env="ENABLE_RAG_AGENT")
    ENABLE_TEMPORAL_AGENT: bool = Field(default=True, env="ENABLE_TEMPORAL_AGENT")

    # Parallel Execution
    MAX_CONCURRENT_AGENTS: int = Field(default=3, env="MAX_CONCURRENT_AGENTS")
    AGENT_TIMEOUT_SECONDS: int = Field(default=30, env="AGENT_TIMEOUT_SECONDS")

    # LLM Configuration
    LLM_TEMPERATURE: float = Field(default=0.1, env="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: int = Field(default=2000, env="LLM_MAX_TOKENS")

    # Language Settings
    DEFAULT_LANGUAGE: str = Field(default="el", env="DEFAULT_LANGUAGE")
    ENCODING: str = Field(default="utf-8", env="ENCODING")

    # Rate Limiting
    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")
    RETRY_DELAY: int = Field(default=2, env="RETRY_DELAY")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
try:
    settings = Settings()
except Exception as e:
    print(f"Error loading configuration: {e}")
    print("Please ensure .env file exists with required settings")
    raise


def get_documents_path() -> Path:
    """Get absolute path to documents directory."""
    return PROJECT_ROOT / settings.DOCUMENTS_DIR


def get_vectorstore_path() -> Path:
    """Get absolute path to vectorstore directory."""
    path = PROJECT_ROOT / settings.VECTORSTORE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_text_splitter_separators() -> list:
    """Get Greek-aware text splitter separators for legal documents."""
    return [
        "\n\nΆρθρο",
        "\n\nΠαράγραφος",
        "\n\nΤμήμα",
        "\n\n",
        "\n",
        ". ",
        " ",
    ]
