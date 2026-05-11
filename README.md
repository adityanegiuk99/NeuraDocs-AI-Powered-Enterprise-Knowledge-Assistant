# 🧠 NeuraDocs — AI-Powered Enterprise Knowledge Assistant

[![CI Pipeline](https://github.com/adityanegiuk99/NeuraDocs-AI-Powered-Enterprise-Knowledge-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/adityanegiuk99/NeuraDocs-AI-Powered-Enterprise-Knowledge-Assistant/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent **RAG (Retrieval-Augmented Generation)** system that enables employees to query internal documents using natural language. Powered by hybrid retrieval (FAISS + BM25), cross-encoder reranking, and Small Language Models for grounded, hallucination-free answers.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐
│   React Frontend │────▶│              FastAPI Backend                 │
│   (Vite + React) │     │                                              │
│                   │     │  ┌──────────┐  ┌───────────┐  ┌──────────┐ │
│  • Chat Interface │     │  │ Auth API │  │ Chat API  │  │Admin API │ │
│  • Admin Dashboard│     │  └────┬─────┘  └─────┬─────┘  └────┬─────┘ │
│  • Document Mgmt  │     │       │              │              │       │
│  • Role-based UI  │     │  ┌────▼──────────────▼──────────────▼─────┐│
│                   │     │  │           RAG Pipeline                  ││
│                   │     │  │  Query → Rewrite → Retrieve → Generate ││
│                   │     │  └─────┬───────────────────────────┬──────┘│
│                   │     │        │                           │       │
│                   │     │  ┌─────▼─────┐          ┌─────────▼──────┐│
│                   │     │  │   FAISS   │          │   LLM Provider ││
│                   │     │  │ + BM25    │          │ (OpenAI/Groq)  ││
│                   │     │  └───────────┘          └────────────────┘│
│                   │     │                                            │
└─────────────────┘     └──────────────────────────────────────────────┘
```

## 🚀 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy (async) |
| **Frontend** | React 18, Vite, Recharts, Lucide Icons |
| **Vector DB** | FAISS (local) / Pinecone (cloud) |
| **Sparse Search** | BM25 (rank-bm25) |
| **Reranking** | Cross-encoder reranking |
| **Embeddings** | HuggingFace Sentence-Transformers (all-MiniLM-L6-v2) |
| **LLM** | OpenAI GPT-4o-mini / Groq (with fallback) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Auth** | JWT (access + refresh tokens) + Role-Based Access Control |
| **Logging** | Structlog (JSON in prod, colored console in dev) |
| **CI/CD** | GitHub Actions (lint, test, Docker build) |
| **Deployment** | Docker Compose |

## 🎯 Features

### ✅ Implemented
- [x] Project architecture & configuration (pydantic-settings)
- [x] Database models — User, Document, Conversation, Message, QueryLog
- [x] JWT authentication with access & refresh tokens
- [x] Role-based access control (Admin, HR, Engineer)
- [x] Document ingestion pipeline (PDF, DOCX, TXT)
- [x] Semantic chunking with section-aware splitting
- [x] Metadata extraction (auto-classification, keyword detection)
- [x] HuggingFace & OpenAI embedding providers
- [x] FAISS vector store with metadata filtering
- [x] BM25 sparse search + Reciprocal Rank Fusion
- [x] Cross-encoder reranking (top-k precision)
- [x] RAG chain with conversational query rewriting
- [x] Retrieval gate (similarity threshold filtering)
- [x] Conversational memory (multi-turn context)
- [x] Evaluation framework (Precision@k, Recall@k, MRR, Faithfulness)
- [x] React chat interface with suggested queries
- [x] Admin dashboard with analytics charts (Recharts)
- [x] Document management UI (upload, filter, delete)
- [x] User management with role editing
- [x] Query logs & performance monitoring
- [x] System health dashboard
- [x] Background document ingestion (FastAPI BackgroundTasks)
- [x] Rate limiting middleware (sliding window)
- [x] Request ID tracking & structured request logging
- [x] Comprehensive test suite (pytest + pytest-asyncio)
- [x] Docker Compose deployment
- [x] CI/CD pipeline (GitHub Actions)

### 🔜 Planned
- [ ] WebSocket streaming for real-time responses
- [ ] Multi-tenant support
- [ ] Pinecone cloud vector store integration
- [ ] PDF viewer with highlighted source passages
- [ ] Email notifications for ingestion status
- [ ] Advanced analytics with query clustering

## 📁 Project Structure

```
neuradocs/
├── backend/
│   ├── app/
│   │   ├── api/              # REST API layer
│   │   │   ├── deps.py       # Auth dependencies (JWT, RBAC)
│   │   │   ├── middleware.py  # Rate limiting, request logging
│   │   │   ├── router.py     # API router aggregation
│   │   │   └── v1/           # Versioned endpoints
│   │   │       ├── auth.py   # Register, login, refresh
│   │   │       ├── chat.py   # Query, conversations, feedback
│   │   │       ├── documents.py  # Upload, list, metadata, delete
│   │   │       └── admin.py  # Users, analytics, health
│   │   ├── core/             # Business logic
│   │   │   ├── ingestion/    # Document processing pipeline
│   │   │   │   ├── parser.py     # PDF/DOCX/TXT parsing
│   │   │   │   ├── chunker.py    # Semantic chunking
│   │   │   │   ├── metadata.py   # Auto-classification
│   │   │   │   └── pipeline.py   # Orchestrator
│   │   │   ├── embeddings/   # Vector embedding providers
│   │   │   │   ├── base.py       # Abstract interface
│   │   │   │   ├── huggingface.py
│   │   │   │   └── openai.py
│   │   │   ├── retrieval/    # Hybrid search subsystem
│   │   │   │   ├── vector_store.py  # FAISS operations
│   │   │   │   ├── hybrid.py       # BM25 + RRF
│   │   │   │   ├── reranker.py     # Cross-encoder
│   │   │   │   └── retriever.py    # Pipeline orchestrator
│   │   │   ├── generation/   # LLM response generation
│   │   │   │   ├── llm.py         # Provider abstraction
│   │   │   │   ├── prompts.py     # System & RAG prompts
│   │   │   │   └── rag_chain.py   # End-to-end RAG pipeline
│   │   │   ├── memory/       # Conversation memory
│   │   │   ├── evaluation/   # RAG quality metrics
│   │   │   └── tasks.py      # Background processing
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── db/               # Database engine & session
│   │   └── utils/            # Security, logging utilities
│   ├── tests/                # Test suite
│   │   ├── conftest.py       # Fixtures & test client
│   │   ├── test_auth.py      # Auth endpoint tests
│   │   ├── test_chat.py      # Chat endpoint tests
│   │   ├── test_documents.py # Document management tests
│   │   └── test_core.py      # Core module unit tests
│   ├── data/                 # Runtime data (uploads, FAISS index)
│   ├── requirements.txt
│   ├── pyproject.toml        # Pytest, ruff, coverage config
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/         # ChatWindow, InputBar, MessageBubble
│   │   │   ├── admin/        # Dashboard with charts
│   │   │   ├── auth/         # LoginForm, ProtectedRoute
│   │   │   └── shared/       # Sidebar navigation
│   │   ├── context/          # AuthContext (React Context)
│   │   ├── services/         # API client (axios)
│   │   ├── App.jsx           # Router & layout
│   │   └── index.css         # Global styles
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── .github/workflows/ci.yml  # CI pipeline
├── docker-compose.yml
└── README.md
```

## ⚙️ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### Backend

```bash
cd backend
cp .env.example .env          # Configure API keys
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # Starts on http://localhost:5173
```

### Docker (Full Stack)

```bash
docker-compose up --build      # Backend: :8000, Frontend: :3000
```

## 🧪 Testing

```bash
cd backend
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test module
pytest tests/test_auth.py -v
pytest tests/test_chat.py -v
pytest tests/test_documents.py -v
```

## 🔒 API Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@company.com", "username": "user", "password": "SecurePass123!", "role": "engineer"}'

# Login (returns JWT tokens)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@company.com", "password": "SecurePass123!"}'

# Query with auth
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the remote work policy?"}'
```

## 📊 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register new user | Public |
| POST | `/api/v1/auth/login` | Login & get tokens | Public |
| POST | `/api/v1/auth/refresh` | Refresh access token | Public |
| GET | `/api/v1/auth/me` | Get current user | Any |
| POST | `/api/v1/chat/query` | Submit RAG query | Any |
| GET | `/api/v1/chat/conversations` | List conversations | Any |
| GET | `/api/v1/chat/history/{id}` | Get message history | Any |
| POST | `/api/v1/chat/feedback` | Submit feedback | Any |
| POST | `/api/v1/documents/upload` | Upload document | Admin/HR |
| GET | `/api/v1/documents/` | List documents | Any |
| GET | `/api/v1/documents/{id}` | Get document details | Any |
| PATCH | `/api/v1/documents/{id}/metadata` | Update metadata | Admin |
| DELETE | `/api/v1/documents/{id}` | Delete document | Admin |
| GET | `/api/v1/admin/health` | System health check | Admin |
| GET | `/api/v1/admin/users` | List all users | Admin |
| GET | `/api/v1/admin/analytics` | Query analytics | Admin |
| GET | `/api/v1/admin/logs` | Query logs | Admin |

## 📄 License

MIT

---

> 🏗️ **Status**: Day 5 — Testing, background processing & middleware hardening complete
