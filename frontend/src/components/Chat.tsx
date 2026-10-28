import { useState } from "react";
import { streamChat, type ChatMessage } from "../api";

type Props = { jobDescription: string; resume: string };

export function Chat({ jobDescription, resume }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    const history: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages([...history, { role: "assistant", content: "" }]);
    setInput("");
    setStreaming(true);
    setError(null);

    try {
      await streamChat(jobDescription, resume, history, (token) => {
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, content: last.content + token };
          return next;
        });
      });
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
          placeholder="e.g. How should I answer 'tell me about yourself'?"
          maxLength={4000}
        />
        <button type="submit" disabled={streaming || !input.trim()}>
          {streaming ? "Thinking…" : "Send"}
        </button>
      </form>
    </section>
  );
}
