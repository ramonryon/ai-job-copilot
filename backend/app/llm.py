"""LLM providers.

The API talks to a small `LLMProvider` interface, so the app runs with OpenAI in
production and with a deterministic offline provider in tests and local dev.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncIterator
from typing import Protocol

from .prompts import ANALYZE_SYSTEM, CHAT_SYSTEM
from .schemas import AnalyzeResponse, ChatMessage

# Skills the offline provider knows how to match. Order = display order.
KNOWN_SKILLS = [
    "React", "TypeScript", "JavaScript", "Next.js", "Python", "FastAPI", "Flask",
    "Django", "Node.js", "Java", "Spring Boot", "REST", "GraphQL", "SQL",
    "PostgreSQL", "MySQL", "MongoDB", "Docker", "Kubernetes", "AWS", "Azure",
    "GCP", "CI/CD", "Jest", "Testing", "LLM", "OpenAI", "LangChain", "RAG",
    "Tailwind", "Salesforce", "Kafka",
]


class LLMProvider(Protocol):
    async def analyze(self, job_description: str, resume: str) -> AnalyzeResponse: ...

    def chat(
        self, job_description: str, resume: str, messages: list[ChatMessage]
    ) -> AsyncIterator[str]: ...


def _has_skill(text: str, skill: str) -> bool:
    pattern = r"(?<![\w.])" + re.escape(skill.lower()) + r"(?![\w])"
    return re.search(pattern, text.lower()) is not None


class OfflineProvider:
    """Deterministic keyword-based provider. No API key, no network."""

    async def analyze(self, job_description: str, resume: str) -> AnalyzeResponse:
        required = [s for s in KNOWN_SKILLS if _has_skill(job_description, s)]
        matched = [s for s in required if _has_skill(resume, s)]
        missing = [s for s in required if s not in matched]
        score = round(100 * len(matched) / len(required)) if required else 0

        return AnalyzeResponse(
            match_score=score,
            summary=(
                f"Offline analysis: the resume mentions {len(matched)} of the "
                f"{len(required)} skills found in the job description. "
                "Set OPENAI_API_KEY for a full AI review."
            ),
            strengths=[f"Resume mentions {s}" for s in matched],
            gaps=[f"No evidence of {s} in the resume" for s in missing],
            suggested_bullets=[],
            interview_questions=[f"Tell me about a project where you used {s}." for s in matched[:3]],
        )

    async def chat(
        self, job_description: str, resume: str, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        last = messages[-1].content
        reply = (
            "Offline mode: set OPENAI_API_KEY to get real coaching. "
            f'You asked: "{last}". Tip: answer with Situation, Action and Result, '
            "using a real example from your resume."
        )
        for word in reply.split(" "):
            yield word + " "


class OpenAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def analyze(self, job_description: str, resume: str) -> AnalyzeResponse:
        completion = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ANALYZE_SYSTEM},
                {
                    "role": "user",
                    "content": f"JOB DESCRIPTION:\n{job_description}\n\nRESUME:\n{resume}",
                },
            ],
        )
        data = json.loads(completion.choices[0].message.content or "{}")
        return AnalyzeResponse.model_validate(data)

    async def chat(
        self, job_description: str, resume: str, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        system = CHAT_SYSTEM.format(job_description=job_description, resume=resume)
        stream = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.5,
            stream=True,
            messages=[{"role": "system", "content": system}]
            + [m.model_dump() for m in messages],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta


def get_provider() -> LLMProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAIProvider(api_key, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    return OfflineProvider()
