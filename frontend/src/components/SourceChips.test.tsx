import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SourceChips } from "./SourceChips";

describe("SourceChips", () => {
  it("shows each source with its excerpt number and preview", () => {
    render(<SourceChips sources={[{ source: "resume.pdf", chunk: 2, preview: "Raised coverage to 87%" }]} />);
    const chip = screen.getByText("resume.pdf #2");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute("title", "Raised coverage to 87%");
  });

  it("renders nothing when there are no sources", () => {
    const { container } = render(<SourceChips sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
