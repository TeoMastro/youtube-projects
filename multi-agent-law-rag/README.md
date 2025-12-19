# Multi-Agent Greek Legal Document RAG System

A production-ready multi-agent system for analyzing Greek legal documents (ΦΕΚ PDFs) using LangChain, LangGraph, and OpenAI.

## Features

- **4 Specialized Agents**:
  - **Ingestion Agent**: Processes PDFs with metadata extraction (ΦΕΚ number, date, type, authority, subject)
  - **RAG Agent**: Hybrid retrieval (semantic + BM25) with pretrained knowledge supplementation
    - Clearly marks information source (RAG documents vs. pretrained knowledge)
  - **Temporal Agent**: Date-based filtering and chronological search
  - **Supervisor Agent**: Orchestrates parallel execution and synthesizes responses

- **Parallel Multi-Agent Execution**: RAG and Temporal agents run concurrently for faster results
- **Hybrid Search**: Combines semantic (vector) search with BM25 keyword matching for better retrieval
- **Greek Text Support**: Full UTF-8 support with Unicode normalization throughout
- **Persistent Vector Store**: ChromaDB with disk persistence
- **Production-Ready**: Error handling, retry logic, progress bars, logging

## Prerequisites

- Python 3.11+
- OpenAI API key
- ~500MB disk space for vector store

## Installation

### 1. Clone or download this repository

```bash
cd multi-agent-law-rag
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.example` to `.env` and add your OpenAI API key:

```bash
cp .env.example .env
```

Edit `.env`:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

## Quick Start

### 1. Validate PDFs

Check that your PDFs are readable:

```bash
python -m src.main validate
```

### 2. Ingest Documents

Process all PDFs into the vector store:

```bash
python -m src.main ingest
```

This will:
- Extract text from each PDF
- Extract metadata (ΦΕΚ number, date, document type, etc.)
- Chunk text (1000 tokens with 200 overlap)
- Generate embeddings
- Store in ChromaDB

### 3. Query the System

#### Interactive Mode

```bash
python -m src.main query -i
```

#### Single Question

```bash
python -m src.main query -q "Ποιοι νόμοι δημοσιεύτηκαν το 2024;"
```

The system will:
- Run 2 agents in parallel (RAG, Temporal)
- Combine their responses
- Return a synthesized answer with citations

### 4. View Statistics

```bash
python -m src.main stats
```

## CLI Commands

| Command | Description | Options |
|---------|-------------|---------|
| `ingest` | Ingest PDFs into vector store | `--force`, `--single <filename>` |
| `query` | Query the system | `-q <question>`, `-i` (interactive) |
| `stats` | Show vector store statistics | |
| `validate` | Validate PDFs | |
| `reset` | Delete vector store | |
| `config-info` | Show configuration | |

## Architecture

### Multi-Agent System

```
User Query
    ↓
┌───────────────┬──────────────┐
│               │              │
RAG Agent   Temporal Agent   (Parallel)
│               │
└───────────────┴──────────────┘
    ↓
Supervisor Agent
    ↓
Final Answer + Citations
```

### Agent Responsibilities

1. **RAG Agent**:
   - Retrieves from local vector store
   - Uses hybrid search (semantic + BM25)
   - Supplements with pretrained knowledge when documents don't fully cover the query
   - Clearly marks information source (RAG documents vs. pretrained knowledge)
   - Best for conceptual queries and exact legal terms

2. **Temporal Agent**:
   - Extracts dates from queries (Greek/English)
   - Filters documents by publication date
   - Sorts chronologically

3. **Supervisor Agent**:
   - Combines RAG and Temporal agent responses
   - Prioritizes based on agent confidence scores
   - Preserves source distinctions (RAG vs. pretrained knowledge)
   - Synthesizes final answer

### Hybrid Retrieval

The system uses **EnsembleRetriever** combining:
- **Semantic Search** (embeddings): Good for "νόμοι για εργασία"
- **BM25 Keyword Search**: Good for "άρθρο 10", "ΦΕΚ 123/Α/2024"

Weights: 50% semantic + 50% BM25 (configurable in `.env`)

### Metadata Extraction

From each ΦΕΚ PDF, the system extracts:
- **ΦΕΚ Number**: "123/Α/2024"
- **Publication Date**: Parsed from Greek date formats
- **Document Type**: Νόμος, Απόφαση, Προεδρικό Διάταγμα, etc.
- **Authority**: Ministry or issuing body
- **Subject**: Document title/heading

This enables the Temporal Agent to filter by date and improves result relevance.

## Configuration

Edit `.env` to customize:

```bash
# Models
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Retrieval
RETRIEVAL_TOP_K=5
SEMANTIC_WEIGHT=0.5
BM25_WEIGHT=0.5

# Multi-Agent
ENABLE_RAG_AGENT=true
ENABLE_TEMPORAL_AGENT=true

# Parallel Execution
MAX_CONCURRENT_AGENTS=3
AGENT_TIMEOUT_SECONDS=30
```

## Example Queries

### Temporal Queries
```
"Ποιοι νόμοι δημοσιεύτηκαν το 2024;"
"Νομοθεσία μετά το 2020"
"ΦΕΚ πριν το 2023"
```

### Semantic Queries
```
"Νόμοι για εργασία"
"Τι προβλέπει το άρθρο 10;"
"Περίληψη ΦΕΚ 123"
```

### Queries with Pretrained Knowledge Supplementation
```
"Τι είναι το ΦΕΚ;"  (Pretrained knowledge supplements if not in documents)
"Σύγκριση με Ευρωπαϊκή νομοθεσία" (Documents + general legal knowledge)
```

## Troubleshooting

### PDF Extraction Issues

If PDFs fail to extract:
1. Check PDF validity: `python -m src.main validate`
2. Some scanned PDFs may need OCR (not included)
3. Use `--force` to re-ingest: `python -m src.main ingest --force`

### Greek Encoding

- All files use UTF-8 encoding
- Greek text is normalized (NFC) for consistency
- If you see garbled text, check your terminal encoding

### API Rate Limits

- The system uses retry logic with exponential backoff
- Configure `MAX_RETRIES` and `RETRY_DELAY` in `.env`
- Batch processing reduces API calls

### Empty Results

- Check vector store: `python -m src.main stats`
- Ensure documents are ingested: `python -m src.main ingest`
- Try broader queries first

## Development

### Code Structure

```
src/
├── agents/          # Multi-agent system
├── vectorstore/     # ChromaDB and embeddings
├── utils/           # Utilities (PDF, text, validation)
├── config.py        # Configuration management
└── main.py          # CLI interface
```

### Adding New Agents

1. Create new agent in `src/agents/`
2. Inherit from `BaseAgent`
3. Implement `execute(state)` method
4. Add to `graph.py` workflow
5. Update `state.py` if needed

### Running Tests

```bash
pytest tests/
```

## License

This project is for educational and research purposes.

## Credits

Built with:
- [LangChain](https://python.langchain.com/) - LLM framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [OpenAI](https://openai.com/) - LLM and embeddings

## Support

For issues or questions, please check:
- Configuration in `.env`
- Logs in `logs/` directory
- Vector store stats: `python -m src.main stats`
