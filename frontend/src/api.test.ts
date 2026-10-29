import { describe, expect, it } from "vitest";
import { errorDetail, parseSseChunk } from "./api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("errorDetail", () => {
  it("explains a server or gateway error instead of blaming the input", async () => {
    const res = new Response("<html>Bad Gateway</html>", { status: 502 });
    expect(await errorDetail(res, "fallback")).toContain("HTTP 502");
  });

  it("names the field that is too long", async () => {
    const res = json(422, { detail: [{ loc: ["body", "resume"], type: "string_too_long" }] });
    expect(await errorDetail(res, "fallback")).toBe("The resume is too long (max. 20,000 characters).");
  });

  it("uses the server message when there is one", async () => {
    expect(await errorDetail(json(400, { detail: "Only PDF files" }), "fallback")).toBe("Only PDF files");
  });
});

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
