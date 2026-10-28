import json
import logging
import os
from dataclasses import asdict

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from .llm import LLMProvider, OfflineProvider, get_provider
from .rag import (
    MAX_FILE_BYTES,
    DocumentError,
    KnowledgeBase,
    extract_text,
    format_context,
    get_knowledge_base,
    to_sources,
)
from .schemas import AnalyzeRequest, AnalyzeResponse, ChatRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ai-job-copilot")

app = FastAPI(title="AI Job Copilot", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Session-Id"],
)


def provider_dep() -> LLMProvider:
    return get_provider()


def knowledge_dep() -> KnowledgeBase:
    return get_knowledge_base()


def session_dep(x_session_id: str = Header(default="", alias="X-Session-Id")) -> str:
    # The browser generates a random id per visitor; it scopes uploaded documents.
    if not (8 <= len(x_session_id) <= 64) or not x_session_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Missing or invalid X-Session-Id header.")
    return x_session_id


@app.get("/api/health")
def health(provider: LLMProvider = Depends(provider_dep)) -> dict:
    mode = "offline" if isinstance(provider, OfflineProvider) else "openai"
    return {"status": "ok", "mode": mode}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, provider: LLMProvider = Depends(provider_dep)) -> AnalyzeResponse:
    try:
        result = await provider.analyze(req.job_description, req.resume)
    except (ValidationError, json.JSONDecodeError) as exc:
        logger.warning("LLM returned an invalid analysis: %s", exc)
        raise HTTPException(status_code=502, detail="The AI returned an invalid answer. Try again.") from exc
    logger.info("analysis done score=%s", result.match_score)
    return result


@app.get("/api/documents")
def list_documents(
    session_id: str = Depends(session_dep), kb: KnowledgeBase = Depends(knowledge_dep)
) -> list[dict]:
    return kb.list_documents(session_id)


@app.post("/api/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Depends(session_dep),
    kb: KnowledgeBase = Depends(knowledge_dep),
) -> dict:
    data = await file.read(MAX_FILE_BYTES + 1)
    filename = os.path.basename(file.filename or "document.txt")
    try:
        text = extract_text(filename, data)
        chunks = kb.add_document(session_id, filename, text)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logger.info("document ingested chunks=%s", chunks)
    return {"source": filename, "chunks": chunks}


@app.delete("/api/documents", status_code=204)
def clear_documents(
    session_id: str = Depends(session_dep), kb: KnowledgeBase = Depends(knowledge_dep)
) -> None:
    kb.clear(session_id)


@app.post("/api/chat")
async def chat(
    req: ChatRequest,
    session_id: str = Depends(session_dep),
    provider: LLMProvider = Depends(provider_dep),
    kb: KnowledgeBase = Depends(knowledge_dep),
) -> StreamingResponse:
    question = req.messages[-1].content
    docs = kb.search(session_id, question)
    context = format_context(docs)

    async def event_stream():
        # First event: which document excerpts were retrieved (the UI shows them as sources).
        yield f"data: {json.dumps({'sources': [asdict(s) for s in to_sources(docs)]})}\n\n"
        try:
            async for token in provider.chat(req.job_description, req.resume, req.messages, context):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:  # noqa: BLE001 - report to the client instead of dropping the stream
            logger.exception("chat stream failed")
            yield f"data: {json.dumps({'error': 'The AI is unavailable right now.'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
