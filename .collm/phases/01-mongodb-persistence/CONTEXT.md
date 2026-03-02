# Phase 1: MongoDB Persistence Layer

## Context Source
Discussion held: 2026-03-02

## Goals

1. **Store processed documents for reuse** — Avoid re-processing documents; persist tree structures for retrieval
2. **Enable querying by metadata** — Find documents by attributes without scanning all trees

## Approach

### Infrastructure
- MongoDB via docker-compose (local development)
- Single container setup for simplicity

### Storage Model
- Store complete tree JSON in MongoDB
- Include processing metadata alongside tree
- Document-oriented: one document per processed file version

### Versioning
- Each re-processing creates a new version
- Retain full history for temporal queries
- `is_latest` flag for quick access to current version
- Enables: "What did this document look like on date X?"

### Queryable Metadata
| Field | Description |
|-------|-------------|
| `filename` | Original filename |
| `file_path` | Source path |
| `upload_date` | When document was added |
| `page_count` | Number of pages |
| `token_count` | Approximate tokens processed |
| `model_used` | OpenAI model for processing |
| `processing_version` | PageIndex version/config hash |
| `tags` | User-defined tags |
| `doc_type` | Document category (financial, legal, etc.) |

### Version Document Schema
```json
{
  "document_id": "uuid",
  "version": 3,
  "created_at": "ISO-8601",
  "is_latest": true,
  "tree": { ... },
  "metadata": {
    "filename": "report.pdf",
    "page_count": 42,
    "token_count": 15000,
    "model_used": "gpt-4o-2024-11-20",
    ...
  }
}
```

## Constraints
- Local MongoDB only (docker-compose)
- Should integrate with existing CLI (`run_pageindex.py`)
- Don't break current file-based output (make persistence optional)

## Open Questions
- [ ] CLI flags for persistence: `--persist` / `--no-persist`?
- [ ] Connection string configuration (env var vs config.yaml)?
- [ ] Should we add a query CLI or just storage for now?

## Out of Scope (for this phase)
- Query/retrieval API server
- Authentication/authorization
- Multi-tenant isolation
- Cloud Atlas integration

---
*Context captured: 2026-03-02*
