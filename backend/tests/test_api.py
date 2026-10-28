from fastapi.testclient import TestClient

from app.llm import OfflineProvider
from app.main import app, provider_dep

app.dependency_overrides[provider_dep] = lambda: OfflineProvider()
client = TestClient(app)

JOB = "Full-Stack Developer with React, TypeScript and Python. Build REST APIs and LLM features with OpenAI."
RESUME = "Software Engineer with 9 years of React and TypeScript, Node.js and Python, building REST APIs."


def test_health_reports_offline_mode():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "mode": "offline"}


def test_analyze_scores_matched_skills():
    res = client.post("/api/analyze", json={"job_description": JOB, "resume": RESUME})
    assert res.status_code == 200
    body = res.json()
    # Job asks for React, TypeScript, Python, REST, LLM, OpenAI -> resume has 4 of 6.
    assert body["match_score"] == 67
    assert any("React" in s for s in body["strengths"])
    assert any("OpenAI" in g for g in body["gaps"])


def test_skill_matching_does_not_confuse_java_and_javascript():
    res = client.post(
        "/api/analyze",
        json={"job_description": "We need Java and Spring Boot engineers.", "resume": RESUME + " JavaScript."},
    )
    gaps = res.json()["gaps"]
    assert any("Java" in g and "JavaScript" not in g for g in gaps)


def test_analyze_rejects_short_input():
    res = client.post("/api/analyze", json={"job_description": "short", "resume": RESUME})
    assert res.status_code == 422


def test_chat_streams_tokens_and_finishes():
    payload = {
        "job_description": JOB,
        "resume": RESUME,
        "messages": [{"role": "user", "content": "How do I explain my React experience?"}],
    }
    with client.stream("POST", "/api/chat", json=payload) as res:
        assert res.status_code == 200
        text = "".join(res.iter_text())
    assert '"token"' in text
    assert text.strip().endswith("data: [DONE]")
