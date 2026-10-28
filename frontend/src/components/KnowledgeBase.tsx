import { useEffect, useRef, useState } from "react";
import { clearDocuments, listDocuments, uploadDocument, type StoredDocument } from "../api";

export function KnowledgeBase() {
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadDocument(file);
      setDocuments(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleClear() {
    setBusy(true);
    setError(null);
    try {
      await clearDocuments();
      setDocuments([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove your documents.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="knowledge" aria-labelledby="knowledge-title">
      <h2 id="knowledge-title">Your career documents</h2>
      <p className="hint">
        Upload your resume, project READMEs or notes (PDF, .md or .txt, up to 2 MB). The interview coach searches
        them before answering. Only you can see your files.
      </p>
      <div className="knowledge-actions">
        <label className="file-button">
          {busy ? "Uploading…" : "Upload document"}
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.md,.txt"
            onChange={handleFile}
            disabled={busy}
            className="visually-hidden"
          />
        </label>
        {documents.length > 0 && (
          <button type="button" className="secondary" onClick={handleClear} disabled={busy}>
            Remove all
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {documents.length > 0 && (
        <ul className="documents">
          {documents.map((doc) => (
            <li key={doc.source}>
              {doc.source} <span className="muted">· {doc.chunks} excerpts</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
