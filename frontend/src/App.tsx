import { useState } from "react";
import { analyze, type Analysis } from "./api";
import { MatchReport } from "./components/MatchReport";
import { Chat } from "./components/Chat";

export default function App() {
  const [jobDescription, setJobDescription] = useState("");
  const [resume, setResume] = useState("");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setAnalysis(await analyze(jobDescription, resume));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <header>
        <h1>AI Job Copilot</h1>
        <p className="subtitle">
          Compare your resume with a job description, see your gaps, and practice the interview with an AI coach.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="inputs">
        <label>
          Job description
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            rows={12}
            placeholder="Paste the job description here"
            required
            minLength={20}
          />
        </label>
        <label>
          Your resume
          <textarea
            value={resume}
            onChange={(e) => setResume(e.target.value)}
            rows={12}
            placeholder="Paste your resume as plain text"
            required
            minLength={20}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Analyzing…" : "Analyze match"}
        </button>
      </form>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {analysis && (
        <>
          <MatchReport analysis={analysis} />
          <Chat jobDescription={jobDescription} resume={resume} />
        </>
      )}
    </main>
  );
}
