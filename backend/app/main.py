import json
import logging
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from .llm import LLMProvider, OfflineProvider, get_provider
from .schemas import AnalyzeRequest, AnalyzeResponse, ChatRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ai-job-copilot")

app = FastAPI(title="AI Job Copilot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def provider_dep() -> LLMProvider:
    return get_provider()


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


@app.post("/api/chat")
async def chat(req: ChatRequest, provider: LLMProvider = Depends(provider_dep)) -> StreamingResponse:
    async def event_stream():
        try:
            async for token in provider.chat(req.job_description, req.resume, req.messages):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:  # noqa: BLE001 - report to the client instead of dropping the stream
            logger.exception("chat stream failed")
            yield f"data: {json.dumps({'error': 'The AI is unavailable right now.'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
