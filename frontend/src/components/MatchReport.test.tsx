import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MatchReport } from "./MatchReport";

describe("MatchReport", () => {
  it("shows the score and hides empty sections", () => {
    render(
      <MatchReport
        analysis={{
          match_score: 75,
          summary: "Good fit.",
          strengths: ["Strong React"],
          gaps: [],
          suggested_bullets: [],
          interview_questions: ["Tell me about a React project."],
        }}
      />,
    );
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("Strong React")).toBeInTheDocument();
    expect(screen.queryByText("Gaps")).not.toBeInTheDocument();
  });
});
