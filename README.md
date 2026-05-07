# 🧠 NeuraDocs — AI-Powered Enterprise Knowledge Assistant

An intelligent RAG (Retrieval-Augmented Generation) system that enables employees to query internal documents using natural language, powered by Small Language Models.

## 🚀 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, FastAPI |
| **Frontend** | React (Vite) |
| **Vector DB** | FAISS (local) / Pinecone (cloud) |
| **Embeddings** | HuggingFace Sentence-Transformers |
| **LLM** | Mistral / LLaMA (with OpenAI API fallback) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Auth** | JWT + Role-Based Access Control |

## 🎯 Planned Features

- [x] Project structure & architecture design
- [ ] Document ingestion pipeline (PDF, DOCX, TXT)
- [ ] Semantic chunking + embedding + vector storage
- [ ] Hybrid retrieval (Dense + BM25 + Reranking)
- [ ] RAG-based response generation
- [ ] Chat interface with conversational memory
- [ ] Role-based access control (Admin, HR, Engineer)
- [ ] Evaluation system (Precision@k, Recall@k, Faithfulness)
- [ ] Admin dashboard with analytics
- [ ] Docker + CI/CD deployment

## 📁 Project Structure

```
neuradocs/
├── backend/
│   ├── app/
│   │   ├── api/           # REST API routes
│   │   ├── core/          # Business logic (ingestion, retrieval, generation)
│   │   ├── models/        # Database models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── db/            # Database setup
│   │   └── utils/         # Security, logging
│   ├── data/              # Uploads, FAISS index, benchmarks
│   ├── requirements.txt
│   └── .env.example
├── frontend/              # React app (coming soon)
├── docker-compose.yml
└── README.md
```

## ⚙️ Setup (Coming Soon)

```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## 📄 License

MIT

---

> 🏗️ **Status**: Project initialization — architecture & foundation phase
