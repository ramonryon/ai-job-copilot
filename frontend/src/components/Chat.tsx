import { useState } from "react";
import { streamChat, type ChatMessage, type Source } from "../api";

type Props = { jobDescription: string; resume: string };

export function Chat({ jobDescription, resume }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateLastMessage(change: (last: ChatMessage) => ChatMessage) {
    setMessages((current) => {
      const next = [...current];
      next[next.length - 1] = change(next[next.length - 1]);
      return next;
    });
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    const history: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages([...history, { role: "assistant", content: "", sources: [] }]);
    setInput("");
    setStreaming(true);
    setError(null);

    try {
      await streamChat(
        jobDescription,
        resume,
        history,
        (token) => updateLastMessage((last) => ({ ...last, content: last.content + token })),
        (sources: Source[]) => updateLastMessage((last) => ({ ...last, sources })),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed.");
    } finally {
      setStreaming(false);
    }
  }

  return (
    <section className="chat" aria-labelledby="chat-title">
      <h2 id="chat-title">Interview coach</h2>
      <ol className="messages" aria-live="polite">
        {messages.map((m, i) => (
          <li key={i} className={`message message-${m.role}`}>
            <span className="visually-hidden">{m.role === "user" ? "You:" : "Coach:"}</span>
            {m.content || "…"}
            {/*
              TODO(Ramon): render m.sources here as small "chips" under the answer,
              e.g. "resume.pdf #2", with the preview text on hover or in a tooltip.
              Each Source has { source, chunk, preview }. Hide the row when the list is empty.
            */}
          </li>
        ))}
      </ol>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <form onSubmit={send} className="chat-form">
        <label htmlFor="chat-input" className="visually-hidden">
          Your message
        </label>
        <input
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. How should I explain my testing experience?"
          maxLength={4000}
        />
        <button type="submit" disabled={streaming || !input.trim()}>
          {streaming ? "Thinking…" : "Send"}
        </button>
      </form>
    </section>
  );
}
