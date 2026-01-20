# EagleEye Lite - Development Log

## Project Overview

EagleEye Lite is a lightweight audit agent for analyzing Chinese financial PDF documents against 34 regulatory rules. This document tracks key architectural decisions, implementation notes, and development history.

## Architecture Decisions

### Decision 1: Dual-Track PDF Parsing

**Date**: 2025-01-19

**Context**: Financial documents come in two forms - digital PDFs (searchable text) and scanned PDFs (images).

**Decision**: Implement a hybrid parser that auto-detects document type based on text density:
- Text density > 100 chars/page → Use pdfplumber
- Text density < 100 chars/page → Fall back to EasyOCR

**Rationale**:
- pdfplumber is fast and accurate for digital PDFs
- EasyOCR provides good Chinese text recognition for scanned documents
- Auto-detection eliminates user configuration burden

**Trade-offs**:
- OCR path is slower (30-60 seconds per page)
- OCR accuracy is lower (~90% for clean scans)

### Decision 2: ChromaDB for Vector Storage

**Date**: 2025-01-19

**Context**: Need persistent vector storage for rule embeddings.

**Options Considered**:
1. FAISS - Fast, but no persistence without additional code
2. Pinecone - Cloud-hosted, requires API key
3. ChromaDB - Lightweight, persistent, local-first

**Decision**: ChromaDB with persistent storage

**Rationale**:
- No external dependencies (runs locally)
- Built-in persistence to disk
- Good Python API with metadata filtering
- Supports semantic search with cosine similarity

### Decision 3: BGE-small-zh for Embeddings

**Date**: 2025-01-19

**Context**: Need Chinese-capable embedding model for rule retrieval.

**Options Considered**:
1. bge-large-zh-v1.5 (2.2GB) - Best accuracy
2. bge-small-zh-v1.5 (100MB) - Good balance
3. OpenAI embeddings - Requires API key

**Decision**: `BAAI/bge-small-zh-v1.5`

**Rationale**:
- 100MB vs 2.2GB saves significant memory
- Still achieves good Chinese text understanding
- Runs locally without API dependency
- Fast inference on CPU

### Decision 4: Sequential Rule Processing

**Date**: 2025-01-19

**Context**: 34 rules need to be evaluated against financial data.

**Options Considered**:
1. Parallel processing - Faster but higher memory
2. Batch processing - Medium memory, medium speed
3. Sequential processing - Lowest memory, slowest

**Decision**: Sequential (one rule at a time)

**Rationale**:
- Optimized for Mac Mini with 8GB RAM
- Memory efficiency is priority over speed
- LLM (if used) already consumes significant memory
- 34 rules is manageable sequentially

### Decision 5: LangGraph for Orchestration

**Date**: 2025-01-19

**Context**: Need to orchestrate multi-step audit workflow.

**Decision**: Use LangGraph StateGraph

**Rationale**:
- TypedDict-based state management
- Built-in support for conditional edges
- Easy to add retry logic and error handling
- Visual graph debugging possible

**Workflow**:
```
parse -> retrieve -> audit (loop) -> report
                        ↑      |
                        └──────┘
```

### Decision 6: Safe Logic Schema Evaluation

**Date**: 2025-01-19

**Context**: `logic_schema` fields contain executable expressions that need evaluation.

**Security Concern**: Direct `eval()` is dangerous.

**Decision**: AST-based safe evaluation with whitelist

**Implementation**:
- Parse expression to AST
- Only allow safe operators (+, -, *, /, >, <, ==, and, or)
- Only allow safe functions (abs, max, min, sum, len, COUNT)
- Substitute Chinese field names with values before evaluation

**Rationale**:
- Prevents code injection
- Allows complex financial calculations
- Handles Chinese variable names natively

## Implementation Notes

### Rule Structure

Each rule in `master_rulebook_v3.jsonl`:

```json
{
  "rule_id": "CL-001",
  "category": "CL",
  "subject": "政府补助真实性：三表强勾稽",
  "trigger_keywords": ["政府补助", "营业外收入", ...],
  "logic_schema": "abs(...) > 0.1",
  "priority": "High",
  "description": "...",
  "source": "...",
  "linked_models": ["FM-001", "FM-004"],
  "audit_procedures": [...]
}
```

### Financial Data Extraction

Financial data is extracted from PDF tables and text using pattern matching:

1. Table extraction via pdfplumber
2. Row label → field name mapping
3. Number parsing with Chinese unit conversion (万 → 10000, 亿 → 100000000)
4. Percentage handling (77% → 0.77)

### Memory Optimization

- Lazy loading for all heavy components (OCR, embeddings, ChromaDB)
- Singleton pattern for Ollama client
- Sequential rule processing
- Clear intermediate state after each rule

### Error Handling

- Continue on rule evaluation errors (log and skip)
- Graceful degradation for missing data
- Comprehensive error messages in final report

## Change Log

### v0.1.0 (2025-01-19)

**Initial Implementation**

- Created project structure
- Implemented all core modules:
  - `eagleeye/gateway/ollama_client.py` - Ollama API wrapper
  - `eagleeye/tools/pdf_parser.py` - Dual-track PDF parsing
  - `eagleeye/tools/ocr_engine.py` - EasyOCR wrapper
  - `eagleeye/rag/indexer.py` - ChromaDB indexing
  - `eagleeye/rag/retriever.py` - Hybrid rule retrieval
  - `eagleeye/graph/state.py` - AuditState TypedDict
  - `eagleeye/graph/nodes.py` - LangGraph nodes
  - `eagleeye/graph/workflow.py` - Workflow builder
  - `eagleeye/audit/evaluator.py` - Logic schema evaluation
  - `eagleeye/audit/reporter.py` - Report generation
  - `eagleeye/models/` - Data models
- Added test suite with mock financial data
- Created index and run scripts

## Known Issues

1. **Complex Logic Schemas**: Some rules have complex nested expressions that may fail AST parsing. Fallback to simple evaluation handles most cases.

2. **OCR Table Extraction**: OCR mode doesn't extract structured tables. Financial data extraction relies on text patterns.

3. **Chinese Character Encoding**: Ensure UTF-8 encoding throughout the pipeline.

## Future Improvements

1. **LLM-Assisted Evaluation**: Use Ollama for complex rule interpretation
2. **Batch PDF Processing**: Process multiple PDFs in a queue
3. **Web Interface**: Flask/FastAPI web UI for uploads
4. **Rule Editor**: GUI for adding/modifying audit rules
5. **Comparative Analysis**: Compare audits across time periods

## Performance Benchmarks

| Operation | Time (typical) |
|-----------|----------------|
| PDF parse (digital, 50 pages) | 2-5 seconds |
| PDF parse (scanned, 50 pages) | 3-5 minutes |
| Rule indexing (34 rules) | 10-15 seconds |
| Full audit (all rules) | 30-60 seconds |
| Report generation | < 1 second |

## Dependencies

Critical dependencies and versions:

| Package | Version | Purpose |
|---------|---------|---------|
| langgraph | >=0.1.0 | Workflow orchestration |
| chromadb | >=0.4.0 | Vector storage |
| sentence-transformers | >=2.2.0 | Embeddings |
| pdfplumber | >=0.10.0 | PDF text extraction |
| easyocr | >=1.7.0 | OCR for scanned PDFs |
| pydantic | >=2.0.0 | Data validation |
| loguru | >=0.7.0 | Logging |

## Contact

For questions or issues, please open a GitHub issue.
