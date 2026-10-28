import type { Source } from "../api";

/** Shows which document excerpts the coach used, under each answer. */
export function SourceChips({ sources }: { sources?: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources">
      <span className="sources-label">Sources:</span>
      <ul>
        {sources.map((s) => (
          <li key={`${s.source}-${s.chunk}`} className="source-chip" title={s.preview}>
            {s.source} #{s.chunk}
          </li>
        ))}
      </ul>
    </div>
  );
}
