import { describe, expect, it } from "vitest";
import { createEmailRenderer } from "../../../src/email/render.js";

describe("createEmailRenderer", () => {
  it("passes the supplied report unchanged to subject, text, and HTML templates", async () => {
    const report = { date: "2026-09-10", balance: 1000 };
    const calls = [];
    const render = createEmailRenderer({
      loadTemplates: async () => ({
        renderSubject: (input) => {
          calls.push(["subject", input]);
          return "  Budget\n";
        },
        renderText: (input) => {
          calls.push(["text", input]);
          return "  <Bank> & account\n";
        },
        renderHtml: (input) => {
          calls.push(["html", input]);
          return "<p>&lt;Bank&gt; &amp; account</p>";
        },
      }),
    });
    expect(await render(report)).toEqual({
      subject: "Budget",
      text: "<Bank> & account",
      html: "<p>&lt;Bank&gt; &amp; account</p>",
    });
    expect(calls).toEqual([
      ["subject", report],
      ["text", report],
      ["html", report],
    ]);
    expect(calls[0][1]).toBe(report);
    expect(calls[1][1]).toBe(report);
    expect(calls[2][1]).toBe(report);
  });

  it("shares compiled templates across concurrent and later renders without caching report data", async () => {
    let loads = 0;
    const render = createEmailRenderer({
      loadTemplates: async () => {
        loads++;
        return {
          renderSubject: ({ name }) => name,
          renderText: ({ name }) => name,
          renderHtml: ({ name }) => name,
        };
      },
    });
    expect(await Promise.all([render({ name: "First" }), render({ name: "Second" })])).toEqual([
      { subject: "First", text: "First", html: "First" },
      { subject: "Second", text: "Second", html: "Second" },
    ]);
    expect(await render({ name: "Third" })).toEqual({ subject: "Third", text: "Third", html: "Third" });
    expect(loads).toBe(1);
  });

  it("retries loading after failure", async () => {
    let loads = 0;
    const failure = new Error("missing template");
    const render = createEmailRenderer({
      loadTemplates: async () => {
        if (++loads === 1) throw failure;
        return { renderSubject: () => "Budget", renderText: () => "Plain", renderHtml: () => "HTML" };
      },
    });
    await expect(render({})).rejects.toBe(failure);
    expect(await render({})).toEqual({ subject: "Budget", text: "Plain", html: "HTML" });
    expect(loads).toBe(2);
  });

  it.each(["renderSubject", "renderText", "renderHtml"])("propagates a failure from %s", async (name) => {
    const failure = new Error("template failed");
    const render = createEmailRenderer({
      loadTemplates: async () => ({
        renderSubject: () => "Budget",
        renderText: () => "Plain",
        renderHtml: () => "HTML",
        [name]: () => {
          throw failure;
        },
      }),
    });
    await expect(render({})).rejects.toBe(failure);
  });
});
