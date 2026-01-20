# EagleEye Lite - 财务审计智能代理系统

[English](./README_EN.md) | 中文

EagleEye Lite 是一个基于 **RAG + LLM** 的财务审计智能系统，能够自动分析中文财务PDF文档，对照34条监管规则进行智能审计。采用LangGraph工作流编排、ChromaDB向量检索、以及双轨PDF解析技术。

## Features

- **Dual-track PDF Parsing**: Automatic detection of digital vs scanned PDFs
  - Digital PDFs: pdfplumber for fast text extraction
  - Scanned PDFs: EasyOCR fallback for image-based documents
- **34 Audit Rules**: Comprehensive Chinese financial regulatory rules covering:
  - CL (Cross-Ledger): 三表勾稽, 资产注水, 隐性债务
  - FM (Financial Manipulation): 融资性贸易, 虚假注资, 募集资金挪用
  - LC (Legal Compliance): 资产负债率监管, 对外担保, 非标融资
  - OP (Operational Risk): 造血能力, 流动性危机, 存货积压
- **RAG Retrieval**: ChromaDB + BGE embeddings for intelligent rule matching
- **LangGraph Workflow**: Sequential rule evaluation with state management
- **Comprehensive Reporting**: Markdown and JSON output formats

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EagleEye Lite Architecture                      │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐     ┌──────────────────────────────────────────────────┐
    │  PDF     │     │              LangGraph Orchestration             │
    │  Input   │────▶│  ┌────────┐   ┌──────────┐   ┌───────────────┐   │
    └──────────┘     │  │ PARSE  │──▶│ RETRIEVE │──▶│    AUDIT      │   │
                     │  │ NODE   │   │  NODE    │   │    NODE       │   │
                     │  └────┬───┘   └────┬─────┘   └───────┬───────┘   │
                     │       │            │                 │           │
                     └───────┼────────────┼─────────────────┼───────────┘
                             │            │                 │
              ┌──────────────┘            │                 └──────────────┐
              ▼                           ▼                                ▼
    ┌─────────────────┐         ┌─────────────────┐              ┌─────────────────┐
    │   PDF Tools     │         │   RAG Engine    │              │   AI Gateway    │
    │ ┌─────────────┐ │         │ ┌─────────────┐ │              │ ┌─────────────┐ │
    │ │ pdfplumber  │ │         │ │  ChromaDB   │ │              │ │   Ollama    │ │
    │ │ + EasyOCR   │ │         │ │  + BGE-M3   │ │              │ │   Client    │ │
    │ └─────────────┘ │         │ └─────────────┘ │              │ └─────────────┘ │
    └─────────────────┘         └─────────────────┘              └─────────────────┘
```

## Requirements

### System Requirements
- Python 3.10+
- 8GB+ RAM recommended
- For OCR: Poppler (pdf2image dependency)

### LLM API (Choose One)

**Option 1: DeepSeek (Recommended for Chinese documents)**
```bash
# Set API key
export DEEPSEEK_API_KEY=sk-your-api-key-here

# Or create .env file
cp .env.example .env
# Edit .env and add your API key
```

**Option 2: OpenAI**
```bash
export OPENAI_API_KEY=sk-your-api-key-here
```
Then update `config/settings.py`:
```python
llm: LLMSettings = LLMSettings(provider="openai", model="gpt-4o-mini")
```

**Option 3: Ollama (Local, Free)**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended model
ollama pull qwen2.5:7b
```
Then update `config/settings.py`:
```python
llm: LLMSettings = LLMSettings(provider="ollama", model="qwen2.5:7b")
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/eagleeye-lite.git
cd eagleeye-lite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Poppler for pdf2image (required for OCR)
# macOS:
brew install poppler

# Ubuntu/Debian:
sudo apt-get install poppler-utils

# Windows:
# Download from https://github.com/oschwartz10612/poppler-windows/releases
```

## Quick Start

### 1. Index Rules

First, index the audit rules into ChromaDB:

```bash
python scripts/index_rules.py
```

### 2. Run Audit

Audit a PDF document:

```bash
# Basic usage
python scripts/run_audit.py /path/to/financial_report.pdf

# With verbose output
python scripts/run_audit.py /path/to/financial_report.pdf -v

# Custom output path
python scripts/run_audit.py /path/to/financial_report.pdf -o my_report.md

# Include JSON output
python scripts/run_audit.py /path/to/financial_report.pdf --json
```

### 3. Run Mock Audit (Testing)

Test with mock financial data without a PDF:

```bash
python scripts/run_audit.py --mock
```

## Configuration

Edit `config/settings.py` to customize:

```python
class LLMSettings:
    # Provider: "deepseek", "openai", "ollama"
    provider = "deepseek"

    # API settings (auto-detected from env vars)
    base_url = "https://api.deepseek.com/v1"
    api_key = None  # Set via DEEPSEEK_API_KEY env var

    # Model settings
    model = "deepseek-chat"  # or "deepseek-coder"

    # RAG settings
    embedding_model = "BAAI/bge-small-zh-v1.5"
    similarity_threshold = 0.35

    # PDF settings
    text_density_threshold = 100  # chars/page for digital detection
    ocr_gpu = False  # CPU mode for Mac Mini
```

## Project Structure

```
EagleEyeLite/
├── README.md
├── DEVELOPMENT_LOG.md
├── requirements.txt
├── master_rulebook_v3.jsonl          # 34 audit rules
├── config/
│   └── settings.py                   # Configuration
├── eagleeye/
│   ├── gateway/
│   │   └── ollama_client.py          # Ollama API wrapper
│   ├── tools/
│   │   ├── pdf_parser.py             # Dual-track PDF parsing
│   │   └── ocr_engine.py             # EasyOCR wrapper
│   ├── rag/
│   │   ├── indexer.py                # ChromaDB indexing
│   │   └── retriever.py              # Rule retrieval
│   ├── graph/
│   │   ├── state.py                  # AuditState TypedDict
│   │   ├── nodes.py                  # LangGraph nodes
│   │   └── workflow.py               # Workflow builder
│   ├── audit/
│   │   ├── evaluator.py              # Logic schema evaluation
│   │   └── reporter.py               # Report generation
│   └── models/
│       ├── rule.py                   # Rule model
│       ├── document.py               # Document & FinancialData
│       └── finding.py                # Finding & AuditReport
├── tests/
│   ├── fixtures/
│   │   └── mock_financial_data.json
│   └── test_pipeline.py
├── scripts/
│   ├── index_rules.py
│   └── run_audit.py
└── output/                           # Generated reports
```

## Rule Categories

| Category | Description | Rules |
|----------|-------------|-------|
| CL | Cross-Ledger (交叉勾稽) | 8 rules |
| FM | Financial Manipulation (财务造假) | 6 rules |
| LC | Legal Compliance (合规监管) | 10 rules |
| OP | Operational Risk (经营风险) | 10 rules |

## API Usage

```python
from eagleeye.graph.workflow import run_audit

# Run audit on a PDF
result = run_audit(
    pdf_path="financial_report.pdf",
    check_all_rules=True
)

print(f"Rules checked: {result['rules_checked']}")
print(f"Violations found: {result['violations_found']}")

# Access findings
for finding in result['findings']:
    print(f"{finding.rule_id}: {finding.rule_subject}")

# Get markdown report
print(result['markdown'])
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_pipeline.py::TestLogicEvaluator -v

# Run with coverage
pytest tests/ --cov=eagleeye --cov-report=html
```

## Sample Output

```
==========================================================
EagleEye Lite - Financial Document Audit
==========================================================
Input: sample_report.pdf
[PARSE] Detected digital PDF, using pdfplumber
[PARSE] Parsed 50 pages
[RETRIEVE] Loaded all 34 rules
[AUDIT] Evaluating rule 1/34: CL-001 - 政府补助真实性
[AUDIT] Violation detected: CL-001
...
[REPORT] Generated report: 5 violations found

==========================================================
AUDIT RESULTS
==========================================================
Rules checked: 34
Violations found: 5

Violations by severity:
  Critical: 2
  High: 2
  Medium: 1
  Low: 0
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
