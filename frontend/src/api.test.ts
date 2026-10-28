import { describe, expect, it } from "vitest";
import { parseSseChunk } from "./api";

describe("parseSseChunk", () => {
  it("collects tokens from data lines", () => {
    const chunk = 'data: {"token":"Hello "}\n\ndata: {"token":"world"}';
    expect(parseSseChunk(chunk)).toEqual({ tokens: ["Hello ", "world"], done: false, error: undefined });
  });

  it("detects the end of the stream", () => {
    expect(parseSseChunk("data: [DONE]").done).toBe(true);
  });

  it("surfaces errors sent by the server", () => {
    expect(parseSseChunk('data: {"error":"down"}').error).toBe("down");
  });
});
