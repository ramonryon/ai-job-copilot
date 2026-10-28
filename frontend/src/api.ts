export type Analysis = {
  match_score: number;
  summary: string;
  strengths: string[];
  gaps: string[];
  suggested_bullets: string[];
  interview_questions: string[];
};

/** A document excerpt the coach used to answer (retrieved by RAG). */
export type Source = { source: string; chunk: number; preview: string };

export type ChatMessage = { role: "user" | "assistant"; content: string; sources?: Source[] };

export type StoredDocument = { source: string; chunks: number };

const SESSION_KEY = "ai-job-copilot-session";
let fallbackId: string | undefined;

/** Random id per browser: scopes uploaded documents to this visitor. */
export function getSessionId(): string {
  try {
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) return saved;
    const id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    // Storage blocked (private mode): fall back to an id for this page load only.
    return (fallbackId ??= crypto.randomUUID());
  }
}

const sessionHeaders = () => ({ "X-Session-Id": getSessionId() });

async function errorDetail(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => null);
  return typeof body?.detail === "string" ? body.detail : fallback;
}

export async function analyze(jobDescription: string, resume: string): Promise<Analysis> {
  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription, resume }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Please check both texts (min. 20 characters)."));
  return res.json();
}

export async function listDocuments(): Promise<StoredDocument[]> {
  const res = await fetch("/api/documents", { headers: sessionHeaders() });
  if (!res.ok) throw new Error(await errorDetail(res, "Could not load your documents."));
  return res.json();
}

export async function uploadDocument(file: File): Promise<StoredDocument> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/documents", { method: "POST", headers: sessionHeaders(), body: form });
  if (!res.ok) throw new Error(await errorDetail(res, "Upload failed."));
  const body = (await res.json()) as { source: string; chunks: number };
  return body;
}

export async function clearDocuments(): Promise<void> {
  const res = await fetch("/api/documents", { method: "DELETE", headers: sessionHeaders() });
  if (!res.ok) throw new Error(await errorDetail(res, "Could not remove your documents."));
}

type ParsedChunk = { tokens: string[]; done: boolean; error?: string; sources?: Source[] };

/** Parses one Server-Sent Events chunk. Exported for tests. */
export function parseSseChunk(chunk: string): ParsedChunk {
  const result: ParsedChunk = { tokens: [], done: false };
  for (const line of chunk.split("\n")) {
    if (!line.startsWith("data: ")) continue;
    const data = line.slice(6);
    if (data === "[DONE]") {
      result.done = true;
      continue;
    }
    const parsed = JSON.parse(data) as { token?: string; error?: string; sources?: Source[] };
    if (parsed.token) result.tokens.push(parsed.token);
    if (parsed.error) result.error = parsed.error;
    if (parsed.sources) result.sources = parsed.sources;
  }
  return result;
}

export async function streamChat(
  jobDescription: string,
  resume: string,
  messages: ChatMessage[],
  onToken: (token: string) => void,
  onSources?: (sources: Source[]) => void,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...sessionHeaders() },
    body: JSON.stringify({
      job_description: jobDescription,
      resume,
      messages: messages.map(({ role, content }) => ({ role, content })),
    }),
  });
  if (!res.ok || !res.body) throw new Error("Chat is unavailable right now.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Events are separated by a blank line; keep any partial event in the buffer.
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const event of events) {
      const parsed = parseSseChunk(event);
      if (parsed.sources) onSources?.(parsed.sources);
      parsed.tokens.forEach(onToken);
      if (parsed.error) throw new Error(parsed.error);
      if (parsed.done) return;
    }
  }
}
