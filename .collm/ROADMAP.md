# Roadmap: PageIndex

## Overview
A vectorless RAG system that builds hierarchical tree indexes from documents and uses LLM reasoning for retrieval, eliminating the need for vector databases and document chunking.

## Current Milestone

**v0.1 Initial Release** (v0.1.0)
Status: Complete
Phases: 1 of 1 complete

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | MongoDB Persistence | 1 | Complete | 2026-03-02 |

## Phase Details

### Phase 1: MongoDB Persistence Layer

**Goal:** Add persistence layer to store processed document trees in MongoDB with versioning and metadata querying

**Depends on:** Nothing (first phase)

**Research:** Unlikely (standard MongoDB patterns)

**Scope:**
- MongoDB via docker-compose
- Document versioning for temporal queries
- Queryable metadata (filename, dates, page count, model, tags)
- CLI integration for persist/retrieve

**Plans:**
- [x] 01-01: MongoDB persistence with versioning and CLI integration — Complete 2026-03-02

---
*Roadmap created: 2026-03-02*
