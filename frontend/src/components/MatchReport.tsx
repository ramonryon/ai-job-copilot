import type { Analysis } from "../api";

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export function MatchReport({ analysis }: { analysis: Analysis }) {
  const level = analysis.match_score >= 70 ? "high" : analysis.match_score >= 40 ? "medium" : "low";

  return (
    <article className="report" aria-labelledby="report-title">
      <h2 id="report-title">Match report</h2>
      <p className={`score score-${level}`}>
        <span className="score-value">{analysis.match_score}%</span> match
      </p>
      <p>{analysis.summary}</p>
      <div className="report-grid">
        <Section title="Strengths" items={analysis.strengths} />
        <Section title="Gaps" items={analysis.gaps} />
        <Section title="Suggested resume bullets" items={analysis.suggested_bullets} />
        <Section title="Likely interview questions" items={analysis.interview_questions} />
      </div>
    </article>
  );
}
