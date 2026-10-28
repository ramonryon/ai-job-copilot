export type Analysis = {
  match_score: number;
  summary: string;
  strengths: string[];
  gaps: string[];
  suggested_bullets: string[];
  interview_questions: string[];
};

export type ChatMessage = { role: "user" | "assistant"; content: string };

export async function analyze(jobDescription: string, resume: string): Promise<Analysis> {
  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription, resume }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : "Please check both texts (min. 20 characters).";
    throw new Error(detail);
  }
  return res.json();
}

/** Parses one Server-Sent Events chunk into tokens. Exported for tests. */
export function parseSseChunk(chunk: string): { tokens: string[]; done: boolean; error?: string } {
  const tokens: string[] = [];
  let done = false;
  let error: string | undefined;
  for (const line of chunk.split("\n")) {
    if (!line.startsWith("data: ")) continue;
    const data = line.slice(6);
    if (data === "[DONE]") {
      done = true;
      continue;
    }
    const parsed = JSON.parse(data) as { token?: string; error?: string };
    if (parsed.token) tokens.push(parsed.token);
    if (parsed.error) error = parsed.error;
  }
  return { tokens, done, error };
}

export async function streamChat(
  jobDescription: string,
  resume: string,
  messages: ChatMessage[],
  onToken: (token: string) => void,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription, resume, messages }),
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
      parsed.tokens.forEach(onToken);
      if (parsed.error) throw new Error(parsed.error);
      if (parsed.done) return;
    }
  }
}
