# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Medical RAG System - A Korean drug recommendation web application that suggests medications based on symptom descriptions using AI-powered hybrid search and retrieval-augmented generation.

## Development Commands

```bash
# Install all dependencies
make install

# Start both frontend and backend dev servers
make dev

# Backend only
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend only
cd frontend && npm run dev

# Run backend tests with coverage
cd backend && pytest -v --cov=app --cov-report=term-missing

# Run single test file
cd backend && pytest tests/test_api.py -v

# Run single test
cd backend && pytest tests/test_api.py::test_health_check -v

# Linting
make lint                           # Both backend and frontend
cd backend && ruff check .          # Backend only
cd frontend && npm run lint         # Frontend only

# Formatting
make format                         # Both
cd backend && ruff format .         # Backend only
cd frontend && npm run format       # Frontend only

# Docker services
make docker-up                      # Start PostgreSQL, Redis, Milvus, Neo4j
make docker-down                    # Stop all services
make docker-logs                    # View logs

# Database migrations
make db-migrate                     # Run Alembic migrations
make db-rollback                    # Rollback one migration

# Data management
make sync-data                      # Sync from data.go.kr API
make build-index                    # Build vector indexes
```

## Architecture

### RAG Pipeline Flow

```
User Query (Korean)
    ↓
Query Embedding (OpenAI text-embedding-3-small, 1536 dim)
    ↓
Parallel Search:
├── Dense Search (Milvus/PGVector cosine similarity) - 70% weight
└── Sparse Search (BGE-M3 SPLADE or BM25) - 30% weight
    ↓
Hybrid Score Merge → Cohere Reranking (optional) → LLM Response (GPT-4o-mini)
```

### Two Search Modes

1. **Milvus + SPLADE Mode** (Primary): Uses Milvus vector DB with BGE-M3 sparse embeddings for multilingual support. Toggle via `ENABLE_MILVUS=true`.
2. **PGVector + BM25 Mode** (Fallback): Uses PostgreSQL pgvector with Korean 2-gram tokenized BM25. Toggle via `ENABLE_MILVUS=false`.

### Backend Structure (`backend/app/`)

- `api/v1/` - REST endpoints (search, chat, drugs, admin, graph, documents)
- `services/` - Business logic layer
  - `rag_engine.py` - Main RAG orchestrator (entry point for search/chat)
  - `milvus_service.py` - Milvus vector operations (hybrid search)
  - `splade_service.py` - BGE-M3 sparse embeddings (100+ languages including Korean)
  - `bm25_search.py` - BM25 + hybrid search with PGVector fallback
  - `llm_service.py` - OpenAI LLM wrapper
  - `embedding.py` - OpenAI embedding wrapper
  - `neo4j_service.py` - Graph database operations (drug interactions)
- `models/` - SQLAlchemy ORM (Drug, DrugVector, Disease, DiseaseVector, Conversation)
- `external/` - API clients (OpenAI, Cohere, data.go.kr, Neo4j, Redis, DuckDB)
- `core/config.py` - Pydantic Settings for all configuration
- `db/` - Database session management and initialization

### Frontend Structure (`frontend/src/`)

- `pages/` - Page components (Home, SearchResults, DrugDetail, VectorSpace, Admin, RAGProcess)
- `components/` - Reusable components with Glassmorphism styling
- `services/` - API client functions (Axios)
- `context/` - React Context (SearchContext, MemoryContext)
- `hooks/` - Custom hooks (useSearch, useChat)

## Key Configuration

Environment variables (`.env` in `backend/`):

```bash
# Required
OPENAI_API_KEY=sk-...            # Embeddings + LLM
DATA_GO_KR_API_KEY=...           # Korean drug data API

# Optional
COHERE_API_KEY=...               # For reranking
NEO4J_PASSWORD=...               # For graph DB

# Search tuning
ENABLE_MILVUS=true               # true: Milvus+SPLADE, false: PGVector+BM25
ENABLE_HYBRID_SEARCH=true
DENSE_WEIGHT=0.7
SPARSE_WEIGHT=0.3
ENABLE_RERANKING=true

# Memory backend
MEMORY_BACKEND=redis             # "redis" or "duckdb"
ENABLE_NEO4J=false
```

## API Endpoints

```
POST /api/v1/search          # Hybrid search with AI response
POST /api/v1/chat            # Conversational RAG with disease info
GET  /api/v1/drugs/{id}      # Drug detail
GET  /api/v1/drugs           # Paginated drug list
GET  /api/v1/vector-space    # 3D visualization data
POST /api/v1/admin/sync      # Trigger data sync
GET  /api/v1/health          # Health check
GET  /api/v1/graph/interactions  # Drug interactions (Neo4j)
```

## Service Ports

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: 5432
- Milvus: 19530
- Redis: 6379
- Neo4j: 7687

## Design Patterns

- **Singleton**: Service instances via `get_*_service()` factory functions with `@lru_cache`
- **Repository**: Database access through service layer
- **Dependency Injection**: FastAPI `Depends()` for DB sessions
- **Lifespan Context**: Application startup/shutdown via FastAPI lifespan manager
- **Async/Await**: Fully async backend (asyncpg, aiosqlite, httpx)

## Important Constraints

- All drug recommendations require medical disclaimer display
- Korean language support is critical (BGE-M3 supports Korean natively; BM25 uses 2-gram tokenization)
- LLM responses add 10-20 seconds latency; consider async/streaming
- Vector embeddings are fixed at 1536 dimensions (OpenAI text-embedding-3-small)
- pytest uses `asyncio_mode = "auto"` - all async tests work automatically
