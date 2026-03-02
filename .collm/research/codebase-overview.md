# Research: Codebase Overview - PageIndex

**Date:** 2026-03-02
**Agent:** Explore
**Topic:** Explore and explain this repository

---

## Project Overview

**PageIndex** is a vectorless, reasoning-based RAG (Retrieval-Augmented Generation) system that builds a hierarchical tree index from long documents and uses LLMs to reason over that index for agentic, context-aware retrieval.

### Problem it Solves
Traditional vector-based RAG relies on semantic similarity rather than true relevance. PageIndex addresses this by:
- Eliminating the need for vector databases
- Removing artificial document chunking
- Providing human-like retrieval through reasoning-based tree search
- Better explainability and traceability with page and section references

The system achieved **98.7% accuracy** on FinanceBench, outperforming traditional vector-based RAG solutions.

---

## Architecture

The codebase follows a clean, modular architecture:

```
oss-pageindex/
├── run_pageindex.py          # Main entry point CLI
├── pageindex/                # Core package
│   ├── __init__.py          # Package exports
│   ├── page_index.py        # Core PDF processing engine
│   ├── page_index_md.py     # Markdown processing
│   ├── utils.py             # Utilities (API calls, logging, config)
│   └── config.yaml         # Default configuration
├── cookbook/                # Example notebooks
├── tests/                   # Test files and sample PDFs
└── tutorials/              # Tutorial content
```

---

## Key Files and Their Purposes

### Entry Points
- **`run_pageindex.py`**: Main CLI entry point that processes PDF or Markdown files and generates tree structures
- **`pageindex/__init__.py`**: Exports main functions (`page_index_main`, `md_to_tree`)

### Core Components
- **`pageindex/page_index.py`** (48KB):
  - Core PDF processing engine
  - Main function: `page_index_main()`
  - Tree building with `tree_parser()`
  - Title checking and validation
  - Summary generation

- **`pageindex/page_index_md.py`** (24KB):
  - Markdown document processing
  - Header-based node extraction
  - Tree thinning capabilities
  - `md_to_tree()` async function

- **`pageindex/utils.py`** (24KB):
  - OpenAI API wrapper functions (sync/async)
  - Token counting with tiktoken
  - `JsonLogger` class for structured logging
  - `ConfigLoader` class for configuration management
  - PDF text extraction utilities

### Configuration
- **`pageindex/config.yaml`**: Default configuration with model settings and thresholds

---

## Dependencies

```txt
openai==1.101.0          # OpenAI API client
pymupdf==1.26.4          # PDF text extraction
PyPDF2==3.0.1           # PDF processing
python-dotenv==1.1.0     # Environment variable management
tiktoken==0.11.0        # Token counting
pyyaml==6.0.2           # YAML configuration parsing
```

---

## Entry Points

### 1. Command Line Interface
```bash
# Process PDF
python3 run_pageindex.py --pdf_path /path/to/document.pdf

# Process Markdown
python3 run_pageindex.py --md_path /path/to/document.md

# With custom options
python3 run_pageindex.py --pdf_path doc.pdf --model gpt-4o-2024-11-20 --max-pages-per-node 5
```

### 2. Python API
```python
from pageindex import page_index_main, md_to_tree

# PDF processing
result = page_index_main('/path/to/document.pdf', opt)

# Markdown processing
tree = await md_to_tree('/path/to/document.md')
```

---

## Design Patterns and Conventions

### 1. Configuration Management
- Centralized configuration via YAML
- `ConfigLoader` class merges defaults with user options
- Environment-based API key management

### 2. Async Architecture
- Heavy use of `async/await` for API calls
- Concurrent processing with `asyncio.gather()`
- Thread pool for parallel operations

### 3. Tree Processing Patterns
- Hierarchical node structure with parent-child relationships
- Node IDs based on hierarchical position (e.g., "0001.0002")
- Recursive tree traversal and manipulation

### 4. Error Handling
- Retry mechanism for API calls (max 10 attempts)
- Graceful degradation when features are disabled
- Comprehensive logging with `JsonLogger`

### 5. Processing Pipeline
1. **PDF/Markdown Extraction**: Convert document to text tokens
2. **Tree Generation**: Build hierarchical structure from sections
3. **Title Validation**: Verify section placement with LLM
4. **Optional Processing**: Summaries, text inclusion, descriptions
5. **Output**: JSON structure with hierarchical nodes

### 6. Modular Design
- Clear separation of concerns (PDF vs Markdown)
- Configurable features via boolean flags
- Optional components can be disabled for performance

---

## Notable Features

- **Tree Thinning**: For Markdown files, can reduce tree complexity based on token thresholds
- **Vision-based Processing**: Can work directly with PDF page images (though current implementation focuses on text)
- **Multi-format Support**: Both PDF and Markdown document processing
- **Flexible Output**: Various optional fields (summaries, text, descriptions)
- **Professional Focus**: Optimized for financial reports, regulatory filings, academic documents

---

## Summary

PageIndex is a well-structured Python project that provides an alternative approach to RAG systems. Instead of using vector embeddings, it builds a hierarchical tree index from documents and uses LLM reasoning to navigate that tree for information retrieval. The codebase is clean, modular, and follows good Python practices with async patterns, centralized configuration, and clear separation of concerns between PDF and Markdown processing.
