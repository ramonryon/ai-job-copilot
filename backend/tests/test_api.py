import pytest
from fastapi.testclient import TestClient

from app.llm import OfflineProvider
from app.main import app, knowledge_dep, provider_dep
from app.rag import KnowledgeBase, OfflineEmbeddings

JOB = "Full-Stack Developer with React, TypeScript and Python. Build REST APIs and LLM features with OpenAI."
RESUME = "Software Engineer with 9 years of React and TypeScript, Node.js and Python, building REST APIs."
SESSION = {"X-Session-Id": "test-session-0001"}
OTHER_SESSION = {"X-Session-Id": "test-session-0002"}

NOTES = """# Testing
I raised test coverage from 42% to 87% with Jest and React Testing Library on a financial platform.

# Performance
I cut the LCP from 4.2 seconds to 2.1 seconds using code splitting and lazy loading.
"""


@pytest.fixture()
def client(tmp_path):
    kb = KnowledgeBase(OfflineEmbeddings(), tmp_path / "kb.json")
    app.dependency_overrides[provider_dep] = lambda: OfflineProvider()
    app.dependency_overrides[knowledge_dep] = lambda: kb
    yield TestClient(app)
    app.dependency_overrides.clear()


def chat_payload(question: str) -> dict:
    return {"job_description": JOB, "resume": RESUME, "messages": [{"role": "user", "content": question}]}


def test_health_reports_offline_mode(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "mode": "offline"}


def test_analyze_scores_matched_skills(client):
    res = client.post("/api/analyze", json={"job_description": JOB, "resume": RESUME})
    assert res.status_code == 200
    body = res.json()
    # Job asks for React, TypeScript, Python, REST, LLM, OpenAI -> resume has 4 of 6.
    assert body["match_score"] == 67
    assert any("React" in s for s in body["strengths"])
    assert any("OpenAI" in g for g in body["gaps"])


def test_skill_matching_does_not_confuse_java_and_javascript(client):
    res = client.post(
        "/api/analyze",
        json={"job_description": "We need Java and Spring Boot engineers.", "resume": RESUME + " JavaScript."},
    )
    gaps = res.json()["gaps"]
    assert any("Java" in g and "JavaScript" not in g for g in gaps)


def test_analyze_rejects_short_input(client):
    res = client.post("/api/analyze", json={"job_description": "short", "resume": RESUME})
    assert res.status_code == 422


def test_upload_list_and_clear_documents(client):
    res = client.post("/api/documents", headers=SESSION, files={"file": ("notes.md", NOTES, "text/markdown")})
    assert res.status_code == 201
    assert res.json()["source"] == "notes.md"
    assert res.json()["chunks"] >= 1

    assert client.get("/api/documents", headers=SESSION).json()[0]["source"] == "notes.md"
    # Another visitor never sees this file.
    assert client.get("/api/documents", headers=OTHER_SESSION).json() == []

    assert client.delete("/api/documents", headers=SESSION).status_code == 204
    assert client.get("/api/documents", headers=SESSION).json() == []


def test_upload_rejects_unsupported_file(client):
    res = client.post("/api/documents", headers=SESSION, files={"file": ("photo.png", b"\x89PNG", "image/png")})
    assert res.status_code == 400


def test_documents_require_session_header(client):
    assert client.get("/api/documents").status_code == 400


def test_chat_streams_sources_then_tokens(client):
    client.post("/api/documents", headers=SESSION, files={"file": ("notes.md", NOTES, "text/markdown")})
    with client.stream("POST", "/api/chat", headers=SESSION, json=chat_payload("How did I improve test coverage?")) as res:
        assert res.status_code == 200
        text = "".join(res.iter_text())
    first_event = text.split("\n\n")[0]
    assert '"sources"' in first_event and "notes.md" in first_event
    assert '"token"' in text
    assert text.strip().endswith("data: [DONE]")


def test_chat_without_documents_sends_empty_sources(client):
    with client.stream("POST", "/api/chat", headers=SESSION, json=chat_payload("Hi")) as res:
        text = "".join(res.iter_text())
    assert text.startswith('data: {"sources": []}')
