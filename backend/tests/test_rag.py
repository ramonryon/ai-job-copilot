"""Retrieval tests: does the knowledge base find the right excerpt for a question?

These work as a tiny retrieval evaluation. If a change to chunking or embeddings
makes the right excerpt stop showing up first, these tests fail.
"""

import pytest

from app.rag import DocumentError, KnowledgeBase, OfflineEmbeddings, extract_text

SESSION = "eval-session-0001"

EXPERIENCE = "\n\n".join(
    [
        "Testing: raised unit test coverage from 42% to 87% with Jest and React Testing Library.",
        "Performance: cut the Largest Contentful Paint from 4.2s to 2.1s with code splitting and lazy loading.",
        "Email automation: built dynamic AMPscript templates so the CRM team could assemble emails alone.",
        "Deployment: shipped applications with Docker Compose on a VPS behind a Cloudflare Tunnel.",
    ]
)

# question -> words that must appear in the top retrieved excerpt
EVAL_SET = {
    "How did you improve test coverage with Jest?": "coverage",
    "What did you do about performance and lazy loading?": "Contentful",
    "Tell me about the AMPscript email templates": "AMPscript",
    "How do you deploy with Docker?": "Docker",
}


@pytest.fixture()
def kb(tmp_path):
    # Small chunks so each paragraph becomes its own excerpt.
    base = KnowledgeBase(OfflineEmbeddings(), tmp_path / "kb.json", chunk_size=120, chunk_overlap=0)
    base.add_document(SESSION, "experience.md", EXPERIENCE)
    return base


@pytest.mark.parametrize("question,expected", EVAL_SET.items())
def test_top_result_is_the_relevant_excerpt(kb, question, expected):
    top = kb.search(SESSION, question, k=1)[0]
    assert expected in top.page_content


def test_search_is_isolated_per_session(kb):
    assert kb.search("someone-else-0001", "test coverage") == []


def test_knowledge_base_persists_to_disk(kb, tmp_path):
    reloaded = KnowledgeBase(OfflineEmbeddings(), tmp_path / "kb.json")
    assert reloaded.list_documents(SESSION) == kb.list_documents(SESSION)


def test_reuploading_a_file_replaces_it(kb):
    kb.add_document(SESSION, "experience.md", "Only one short paragraph now.")
    assert kb.list_documents(SESSION) == [{"source": "experience.md", "chunks": 1}]


def test_extract_text_rejects_empty_and_unknown_files():
    with pytest.raises(DocumentError):
        extract_text("notes.md", b"   ")
    with pytest.raises(DocumentError):
        extract_text("script.exe", b"MZ")
