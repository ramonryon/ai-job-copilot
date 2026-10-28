from typing import Literal

from pydantic import BaseModel, Field

MAX_TEXT = 20_000


class AnalyzeRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=MAX_TEXT)
    resume: str = Field(min_length=20, max_length=MAX_TEXT)


class AnalyzeResponse(BaseModel):
    match_score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[str]
    gaps: list[str]
    suggested_bullets: list[str]
    interview_questions: list[str]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)


class ChatRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=MAX_TEXT)
    resume: str = Field(min_length=20, max_length=MAX_TEXT)
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)
