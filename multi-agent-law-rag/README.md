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
- **Intelligent PDF Extraction**: Multi-layer extraction with automatic OCR fallback via OpenAI Vision API
- **Greek Text Support**: Full UTF-8 support with Unicode normalization throughout
- **Persistent Vector Store**: FAISS with disk persistence
- **LangSmith Integration**: Built-in tracing and monitoring for debugging and optimization
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

**Note on OCR:** The system automatically handles scanned PDFs and documents with font encoding issues (CID codes) using OpenAI Vision API

### 5. (Optional) Configure LangSmith for Monitoring

LangSmith provides powerful tracing and monitoring for your LLM application:

1. Sign up for a free account at [smith.langchain.com](https://smith.langchain.com)
2. Create an API key in your LangSmith dashboard
3. Add to your `.env` file:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key-here
LANGCHAIN_PROJECT=greek-legal-rag
```

Once enabled, all LLM calls, agent executions, and retrievals will be automatically traced in LangSmith. You can:
- View detailed traces of multi-agent execution
- Monitor prompt inputs/outputs
- Track retrieval performance
- Debug issues in real-time
- Analyze latency and costs

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
- Store in FAISS vector store

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

### 4. Evaluate System Performance

Evaluate your RAG system using RAGAS metrics:

```bash
python -m src.main evaluate
```

This will:
- Run all test cases from `evaluation_dataset.json`
- Calculate RAGAS metrics (faithfulness, relevance, precision, recall)
- Generate detailed reports in `evaluation_results/`

See the **Evaluation** section below for more details.

### 5. View Statistics

```bash
python -m src.main stats
```

## CLI Commands

| Command | Description | Options |
|---------|-------------|---------|
| `ingest` | Ingest PDFs into vector store | `--force`, `--single <filename>` |
| `query` | Query the system | `-q <question>`, `-i` (interactive) |
| `evaluate` | Run system evaluation | `--dataset <path>`, `--output-dir <path>` |
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

# LangSmith Monitoring (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-api-key
LANGCHAIN_PROJECT=greek-legal-rag
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

## Evaluation

The system includes evaluation capabilities using **RAGAS metrics** with **LangSmith integration**.

### Quick Start

1. **Review the example dataset:**
   ```bash
   cat evaluation_dataset.json
   ```

2. **Run evaluation:**
   ```bash
   python -m src.main evaluate
   ```

3. **View results:**
   - Console: See immediate summary with key metrics
   - JSON: `evaluation_results/evaluation_results_YYYYMMDD_HHMMSS.json`

### RAGAS Metrics

The system uses industry-standard RAGAS metrics:

- **Faithfulness** (0-1): Are answers grounded in retrieved context? Measures hallucination.
- **Answer Relevancy** (0-1): How relevant is the answer to the question?
- **Context Precision** (0-1): Are retrieved documents relevant to the expected answer?
- **Context Recall** (0-1): Do retrieved documents contain the information needed for the expected answer?

Note: `expected_answer` in the dataset is used by Context Precision and Context Recall to evaluate retrieval quality.

### Creating Your Evaluation Dataset

Edit `evaluation_dataset.json` to add your own test cases:

```json
{
  "test_cases": [
    {
      "id": "test_001",
      "question": "Your Greek legal question here",
      "expected_answer": "The expected content or facts that should be retrieved"
    }
  ]
}
```

Each test case only requires:
- **id**: Unique identifier for the test
- **question**: The query to send to the system
- **expected_answer**: Ground truth used by RAGAS to evaluate retrieval quality

### LangSmith Integration

With LangSmith enabled (see Configuration), you get additional benefits:

1. **Automatic Tracing**: Every evaluation run is traced in LangSmith
2. **Visual Debugging**: See agent execution flow, LLM calls, and retrievals
3. **Comparison**: Compare different model configurations or prompts
4. **Human Feedback**: Add labels and feedback directly in LangSmith UI
5. **Cost Tracking**: Monitor API costs per evaluation run

Access your traces at [smith.langchain.com](https://smith.langchain.com) in your project.

## Troubleshooting

### PDF Extraction Issues

The system uses a multi-layer extraction strategy:
1. **pdfplumber** - Tries standard text extraction first
2. **PyMuPDF** - Falls back for better font handling
3. **OpenAI Vision API** - Automatically uses OCR for scanned PDFs or documents with CID codes

If PDFs still fail to extract:
1. Check PDF validity: `python -m src.main validate`
2. Ensure `ENABLE_OCR=true` in `.env` (default)
3. Use `--force` to re-ingest: `python -m src.main ingest --force`

**CID Codes (Character ID)**: If you see `(cid:123)` in extracted text, these indicate font encoding issues. The system automatically detects this and falls back to OCR extraction.

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
├── vectorstore/     # FAISS and embeddings
├── evaluation/      # RAGAS evaluation
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
- [FAISS](https://github.com/facebookresearch/faiss) - Vector database
- [RAGAS](https://docs.ragas.io/) - RAG evaluation framework
- [OpenAI](https://openai.com/) - LLM and embeddings

## Support

For issues or questions, please check:
- Configuration in `.env`
- Logs in `logs/` directory
- Vector store stats: `python -m src.main stats`
