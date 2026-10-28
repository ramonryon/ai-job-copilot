# AI Job Copilot

Compare your resume with a job description, see where you match and where you fall short, and practice the interview with an AI coach that streams its answers in real time.

**Live demo:** [copilot.ramonryon.com.br](https://copilot.ramonryon.com.br)

**Stack:** React + TypeScript (Vite) · Python + FastAPI · OpenAI API · Docker · GitHub Actions

<!-- Add a screenshot or GIF here once it is running: docs/demo.gif -->

## Features

- **Match analysis:** a 0–100 score, strengths, gaps, suggested resume bullets and likely interview questions.
- **Interview coach chat:** streams answers token by token over Server-Sent Events.
- **Honest by design:** the prompts forbid inventing experience; suggestions only reword facts that are already in the resume.
- **Runs without an API key:** an offline provider does keyword matching, so the app, the tests and CI never depend on a paid API.

## Architecture

```
Browser (React + TS)
   │  POST /api/analyze   → JSON report
   │  POST /api/chat      → text/event-stream (tokens)
   ▼
FastAPI ── LLMProvider (interface)
              ├── OpenAIProvider   (OPENAI_API_KEY set)
              └── OfflineProvider  (no key: deterministic keyword matching)
```

## Technical decisions

| Decision | Why |
| --- | --- |
| `LLMProvider` interface with two implementations | Swap models or vendors without touching the API; tests run offline and free. |
| JSON mode + Pydantic validation for the analysis | The UI never renders malformed AI output; invalid answers return a clear 502. |
| Server-Sent Events for chat | Simpler than WebSockets for one-way streaming and works through standard proxies. |
| Input limits on every field | Keeps token costs predictable and blocks oversized payloads. |
| Dependency injection for the provider | Tests override it with `app.dependency_overrides`. |

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

- [ ] Upload the resume as PDF and extract the text
- [ ] Save past analyses (PostgreSQL)
- [ ] Rate limiting per IP
- [x] Deploy with Docker Compose on a VPS, exposed through a Cloudflare Tunnel
- [ ] Track token usage and latency per request
