# HybridRAG

**Modern production-grade RAG platform** — semantic retrieval, metadata-aware search, LLM evaluation, and async ingestion at scale.

---

## Architecture

```
                          ┌──────────────┐
                          │  User Upload  │
                          └──────┬───────┘
                                 ▼
                        ┌─────────────────┐
                        │ Semantic Chunking│
                        └────────┬────────┘
                                 ▼
                        ┌─────────────────┐
                        │Metadata Extraction│
                        └────────┬────────┘
                                 ▼
                           ┌──────────┐
                           │Embeddings │
                           └─────┬────┘
                                 ▼
                          ┌──────────────┐
                          │  Chroma Cloud │
                          └──────┬───────┘
                                 ▼
                          ┌──────────────┐
                          │HyDE Retrieval │
                          └──────┬───────┘
                                 ▼
                      ┌─────────────────────┐
                      │Metadata-Aware Search │
                      └──────────┬──────────┘
                                 ▼
                          ┌───────────────┐
                          │Cohere Reranking│
                          └───────┬───────┘
                                  ▼
                          ┌──────────────┐
                          │ GPT-4o Answer│
                          └──────────────┘
```

---

## Features

### Retrieval

- **Semantic chunking** — adaptive splitting based on embedding similarity
- **Metadata extraction** — auto-tagged chunks with document-level context
- **Metadata-aware retrieval** — filtered vector search using extracted metadata
- **HyDE** — hypothetical document embeddings for query-document gap bridging
- **Cohere reranking** — cross-encoder scoring on top of vector results

### Evaluation

- **LLM-as-judge** — GPT-4o evaluates every response on four axes
- **Faithfulness** — hallucination detection against source chunks
- **Groundedness** — factual anchoring to retrieved context
- **Relevance** — query-response alignment scoring
- **Citation** — source attribution accuracy

### Infrastructure

- **Async ingestion pipeline** — non-blocking document processing
- **Celery workers** — background task execution with retries
- **Redis queue** — reliable job brokering
- **Flower dashboard** — real-time worker monitoring
- **Chroma Cloud** — managed vector storage with serverless scaling

---

## Tech Stack

| Layer           | Technology                                                |
| --------------- | --------------------------------------------------------- |
| **Backend**     | FastAPI, Python 3.13, LangChain                           |
| **Frontend**    | React 19, TypeScript, TailwindCSS 4                       |
| **Auth**        | Clerk (RBAC admin access)                                 |
| **LLM**         | OpenAI GPT-4o                                             |
| **Embeddings**  | text-embedding-3-large                                    |
| **Vector DB**   | Chroma Cloud                                              |
| **Queue**       | Redis + Celery                                            |
| **Monitoring**  | Flower, LangSmith                                         |
| **Database**    | PostgreSQL (Railway)                                      |
| **Object Store**| Backblaze B2                                              |
| **Reranker**    | Cohere                                                    |
| **Package Mgr** | uv                                                        |

---

## Setup

### Prerequisites

- Python 3.13+
- Node.js 20+
- PostgreSQL, Redis, Chroma Cloud accounts

### Backend

```bash
cd backend
uv sync
cp .env.example .env   # fill in your keys
uv run uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_CLERK_PUBLISHABLE_KEY
npm run dev
```

### Workers

```bash
cd backend
uv run celery -A workers.celery_app worker --loglevel=info
uv run celery -A workers.celery_app flower   # monitoring on :5555
```

---

## Environment Variables

| Variable                    | Purpose                        |
| --------------------------- | ------------------------------ |
| `DATABASE_URL`              | PostgreSQL connection string   |
| `OPENAI_API_KEY`            | OpenAI API key                 |
| `OPENAI_MODEL`              | Model name (default: `gpt-4o`) |
| `CHROMA_API_KEY`            | Chroma Cloud API key           |
| `CHROMA_TENANT`             | Chroma Cloud tenant ID         |
| `CHROMA_DATABASE`           | Chroma database name           |
| `COHERE_API_KEY`            | Cohere API key (reranking)     |
| `CLERK_SECRET_KEY`          | Clerk backend secret           |
| `CLERK_JWKS_URL`            | Clerk JWKS endpoint            |
| `REDIS_URL`                 | Redis connection string        |
| `B2_KEY_ID` / `B2_APPLICATION_KEY` | Backblaze B2 credentials |
| `LANGSMITH_API_KEY`         | LangSmith tracing (optional)   |
| `NEO4J_URI`                 | Neo4j connection (future)      |

Full list in `backend/.env`.

---

## Roadmap

- **GraphRAG / HybridRAG** — combine vector search with knowledge graph traversal
- **Multi-modal retrieval** — CLIP-based image embeddings alongside text
- **Streaming responses** — server-sent events for real-time answer generation
- **Model playground** — A/B test different LLMs and embedding strategies

---

## Deployment

Designed for **Railway** deployment. Backend and workers run as separate services, with Redis and PostgreSQL provisioned as Railway plugins. Frontend builds to static assets served via CDN.

---

## License

MIT © 2026 — see [LICENSE](./LICENSE)
