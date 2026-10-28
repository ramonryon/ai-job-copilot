import { describe, expect, it } from "vitest";
import { parseSseChunk } from "./api";

describe("parseSseChunk", () => {
  it("collects tokens from data lines", () => {
    const chunk = 'data: {"token":"Hello "}\n\ndata: {"token":"world"}';
    expect(parseSseChunk(chunk).tokens).toEqual(["Hello ", "world"]);
  });

  it("detects the end of the stream", () => {
    expect(parseSseChunk("data: [DONE]").done).toBe(true);
  });

  it("surfaces errors sent by the server", () => {
    expect(parseSseChunk('data: {"error":"down"}').error).toBe("down");
  });

  it("reads the retrieved sources sent before the answer", () => {
    const chunk = 'data: {"sources":[{"source":"resume.pdf","chunk":2,"preview":"Raised coverage"}]}';
    expect(parseSseChunk(chunk).sources).toEqual([{ source: "resume.pdf", chunk: 2, preview: "Raised coverage" }]);
  });
});
