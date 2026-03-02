# Project: PageIndex

## Description

A vectorless, reasoning-based RAG system that transforms long PDF/Markdown documents into hierarchical tree structures and uses LLM reasoning for human-like retrieval — achieving 98.7% accuracy on FinanceBench.

## Core Value

Users can query long professional documents and get accurate, traceable answers without vector databases or artificial chunking — using reasoning-based tree search instead of semantic similarity.

## Requirements

### Validated (Shipped)

- ✓ MongoDB persistence layer for document trees — Phase 1
- ✓ Document versioning with temporal query support — Phase 1
- ✓ Metadata querying (filename, tags, dates) — Phase 1
- ✓ CLI `--persist` flag for optional persistence — Phase 1

### Active (In Progress)

- [To be defined for next phase]

### Planned (Next)

- [To be defined during planning]

### Out of Scope

- Query/retrieval API server (Phase 1 explicitly excluded)
- Authentication/authorization (deferred)
- Multi-tenant isolation (deferred)
- MongoDB Atlas/cloud integration (deferred)

## Constraints

- Local MongoDB via docker-compose (dev mode, no auth)
- Optional persistence — existing file-based output must be preserved

## Success Criteria

- Core value is achieved: reasoning-based retrieval outperforms vector similarity for professional documents
- Document versioning enables temporal queries

## Key Decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| MongoDB for persistence | Document-oriented, flexible schema, good Python support | 2026-03-02 | Active |
| Versioning via is_latest flag | Efficient latest version queries without complex queries | 2026-03-02 | Active |
| Optional persistence (--persist flag) | Backward compatibility, incremental migration | 2026-03-02 | Active |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3 |
| LLM API | OpenAI (GPT-4o) |
| PDF Processing | PyMuPDF, PyPDF2 |
| Token Counting | tiktoken |
| Configuration | YAML |
| Database | MongoDB 7.0 (via docker-compose) |
| Database Driver | pymongo 4.6.0 |

---
*Created: 2026-03-02*
*Last updated: 2026-03-02 after Phase 1*
