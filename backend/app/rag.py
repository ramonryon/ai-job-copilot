"""Retrieval-Augmented Generation (RAG) knowledge base built with LangChain.

Flow:
  upload -> extract text -> split into chunks -> embed -> vector store
  question -> embed -> similarity search (only this session's chunks) -> context for the LLM

Each browser session gets its own documents: every chunk carries a `session_id`
in its metadata and every search filters on it, so visitors never see each
other's files.
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_DOCUMENTS_PER_SESSION = 5
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 4


class DocumentError(ValueError):
    """Raised for files we refuse to ingest (wrong type, too big, empty)."""


class OfflineEmbeddings(Embeddings):
    """Bag-of-words hashing embeddings: free, deterministic, no network.

    Not semantic like a real model, but texts that share words end up close,
    which is enough for local development and meaningful retrieval tests.
    """

    def __init__(self, size: int = 512) -> None:
        self.size = size

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.size
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            if len(token) < 3:
                continue
            index = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.size
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def extract_text(filename: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentError("Only PDF, Markdown (.md) and text (.txt) files are supported.")
    if len(data) > MAX_FILE_BYTES:
        raise DocumentError("File is larger than 2 MB.")

    if extension == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # noqa: BLE001 - pypdf raises many error types
            raise DocumentError("Could not read this PDF.") from exc
    else:
        text = data.decode("utf-8", errors="ignore")

    if not text.strip():
        raise DocumentError(
            "No text found in the file. If it is a scanned PDF, export it again as a text PDF."
        )
    return text


@dataclass
class SourceInfo:
    source: str
    chunk: int
    preview: str


class KnowledgeBase:
    def __init__(
        self,
        embeddings: Embeddings,
        path: Path | None = None,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self.embeddings = embeddings
        self.path = path
        if path and path.exists():
            self.store = InMemoryVectorStore.load(str(path), embeddings)
        else:
            self.store = InMemoryVectorStore(embeddings)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def _persist(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.store.dump(str(self.path))

    def _session_items(self, session_id: str) -> list[tuple[str, dict]]:
        return [
            (doc_id, item["metadata"])
            for doc_id, item in self.store.store.items()
            if item["metadata"].get("session_id") == session_id
        ]

    def list_documents(self, session_id: str) -> list[dict]:
        counts: dict[str, int] = {}
        for _, metadata in self._session_items(session_id):
            counts[metadata["source"]] = counts.get(metadata["source"], 0) + 1
        return [{"source": source, "chunks": n} for source, n in sorted(counts.items())]

    def add_document(self, session_id: str, filename: str, text: str) -> int:
        existing = {d["source"] for d in self.list_documents(session_id)}
        if filename in existing:
            self.remove_document(session_id, filename)
        elif len(existing) >= MAX_DOCUMENTS_PER_SESSION:
            raise DocumentError(f"Limit of {MAX_DOCUMENTS_PER_SESSION} documents reached. Remove one first.")

        chunks = self.splitter.split_text(text)
        docs = [
            Document(
                page_content=chunk,
                metadata={"session_id": session_id, "source": filename, "chunk": i + 1},
            )
            for i, chunk in enumerate(chunks)
        ]
        self.store.add_documents(docs)
        self._persist()
        return len(docs)

    def remove_document(self, session_id: str, filename: str) -> None:
        ids = [doc_id for doc_id, m in self._session_items(session_id) if m["source"] == filename]
        if ids:
            self.store.delete(ids)
            self._persist()

    def clear(self, session_id: str) -> None:
        ids = [doc_id for doc_id, _ in self._session_items(session_id)]
        if ids:
            self.store.delete(ids)
            self._persist()

    def search(self, session_id: str, query: str, k: int = TOP_K) -> list[Document]:
        if not self._session_items(session_id):
            return []
        return self.store.similarity_search(
            query, k=k, filter=lambda doc: doc.metadata.get("session_id") == session_id
        )


def format_context(docs: list[Document]) -> str:
    return "\n\n".join(
        f"[{d.metadata['source']} #{d.metadata['chunk']}]\n{d.page_content}" for d in docs
    )


def to_sources(docs: list[Document]) -> list[SourceInfo]:
    return [
        SourceInfo(
            source=d.metadata["source"],
            chunk=d.metadata["chunk"],
            preview=d.page_content[:160].strip(),
        )
        for d in docs
    ]


def get_embeddings() -> tuple[Embeddings, str]:
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")), "openai"
    return OfflineEmbeddings(), "offline"


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    embeddings, mode = get_embeddings()
    # One file per embedding mode: vectors from different models are not comparable.
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    return KnowledgeBase(embeddings, data_dir / f"knowledge-{mode}.json")
