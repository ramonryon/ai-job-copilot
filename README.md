# AI Job Copilot

Compare your resume with a job description, see where you match and where you fall short, and practice the interview with an AI coach that streams its answers in real time.

**Live demo:** [copilot.ramonryon.com.br](https://copilot.ramonryon.com.br)

**Stack:** React + TypeScript (Vite) · Python + FastAPI · OpenAI API · LangChain (RAG) · Docker · GitHub Actions

<!-- Add a screenshot or GIF here once it is running: docs/demo.gif -->

## Features

- **Match analysis:** a 0–100 score, strengths, gaps, suggested resume bullets and likely interview questions.
- **Interview coach chat:** streams answers token by token over Server-Sent Events.
- **Career knowledge base (RAG):** upload your resume, project READMEs or notes (PDF, Markdown, text). The coach retrieves the most relevant excerpts before answering and cites them.
- **Honest by design:** the prompts forbid inventing experience; suggestions only reword facts that are already in the resume.
- **Runs without an API key:** an offline provider does keyword matching, so the app, the tests and CI never depend on a paid API.

## Architecture

```
Browser (React + TS)
   │  POST /api/analyze     → JSON report
   │  POST /api/documents   → upload PDF / .md / .txt
   │  POST /api/chat        → text/event-stream (sources, then tokens)
   ▼
FastAPI
   ├── LLMProvider (interface)
   │      ├── OpenAIProvider   (OPENAI_API_KEY set)
   │      └── OfflineProvider  (no key: deterministic keyword matching)
   └── KnowledgeBase (LangChain)
          ├── RecursiveCharacterTextSplitter  (800-char chunks, 120 overlap)
          ├── Embeddings: OpenAI text-embedding-3-small | offline hashing
          └── InMemoryVectorStore, persisted to a Docker volume
```

### How RAG works here

1. **Ingestion (on upload):** extract text (pypdf for PDFs) → split into overlapping chunks → embed each chunk → store with `session_id`, file name and chunk number.
2. **Retrieval (on each chat question):** embed the question → similarity search over **this visitor's** chunks only → top 4 excerpts.
3. **Generation:** the excerpts go into the system prompt; the model must cite them like `[resume.pdf #2]` and say so when they do not contain the answer.
4. **Sources:** the first SSE event lists the retrieved excerpts so the UI can show where each answer came from.

## Technical decisions

| Decision | Why |
| --- | --- |
| `LLMProvider` interface with two implementations | Swap models or vendors without touching the API; tests run offline and free. |
| JSON mode + Pydantic validation for the analysis | The UI never renders malformed AI output; invalid answers return a clear 502. |
| Server-Sent Events for chat | Simpler than WebSockets for one-way streaming and works through standard proxies. |
| Input limits on every field | Keeps token costs predictable and blocks oversized payloads. |
| Dependency injection for the provider | Tests override it with `app.dependency_overrides`. |
| LangChain for the RAG pipeline | Standard building blocks (splitters, embeddings, vector stores) that can be swapped without rewriting the app. |
| `InMemoryVectorStore` persisted to disk | Enough for a demo with a few documents per visitor and no extra service to run. The upgrade path is pgvector or Chroma behind the same interface. |
| Documents scoped by a per-browser session id | Visitors never retrieve each other's files. Limits: 5 documents per session, 2 MB per file. |
| Offline hashing embeddings | Free and deterministic, so retrieval tests run in CI without an API key. |
| Retrieval tests as a small evaluation set | `tests/test_rag.py` checks that known questions retrieve the right excerpt first, catching regressions in chunking or embeddings. |

## Running locally

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # optional: add OPENAI_API_KEY
uvicorn app.main:app --reload  # http://localhost:8000/docs
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173 (proxies /api to :8000)
```

**With Docker**

```bash
cp .env.example .env
docker compose up --build      # http://localhost:8080
```

## Tests

```bash
cd backend && python -m pytest -q
cd frontend && npm test
```

CI runs both on every push and pull request.

## Roadmap

- [x] Upload documents (PDF, Markdown, text) and answer with RAG
- [x] Show the retrieved sources as chips under each answer
- [ ] Save past analyses (PostgreSQL)
- [ ] Rate limiting per IP
- [x] Deploy with Docker Compose on a VPS, exposed through a Cloudflare Tunnel
- [ ] Track token usage and latency per request
