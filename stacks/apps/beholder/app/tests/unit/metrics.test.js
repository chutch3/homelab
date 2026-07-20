import { describe, expect, it } from "vitest";

import { createMetrics, startMetricsServer } from "../../src/metrics.js";

const scrape = (metrics) => metrics.registry.metrics();

describe("createMetrics", () => {
  it("records a successful run: timestamp, success=1, per-check findings, duration", async () => {
    const metrics = createMetrics();
    metrics.recordRun({
      findings: [{ check: "floor" }, { check: "drift" }, { check: "drift" }],
      durationSeconds: 2.5,
      now: 1_700_000_000,
    });

    const out = await scrape(metrics);
    expect(out).toContain("beholder_last_run_timestamp_seconds 1700000000");
    expect(out).toContain("beholder_last_run_success 1");
    expect(out).toContain("beholder_run_duration_seconds 2.5");
    expect(out).toContain('beholder_findings{check="drift"} 2');
    expect(out).toContain('beholder_findings{check="floor"} 1');
    expect(out).toContain('beholder_findings{check="raid"} 0');
    expect(out).toContain('beholder_runs_total{outcome="success"} 1');
  });

  it("records a failed run: timestamp set, success=0, failure counted", async () => {
    const metrics = createMetrics();
    metrics.recordFailure({ now: 1_700_000_500 });

    const out = await scrape(metrics);
    expect(out).toContain("beholder_last_run_timestamp_seconds 1700000500");
    expect(out).toContain("beholder_last_run_success 0");
    expect(out).toContain('beholder_runs_total{outcome="failure"} 1');
  });

  it("initializes all five checks to zero before any run", async () => {
    const out = await scrape(createMetrics());
    for (const check of ["floor", "raid", "drift", "schedule", "uncategorized"]) {
      expect(out).toContain(`beholder_findings{check="${check}"} 0`);
    }
  });
});

describe("startMetricsServer", () => {
  it("serves the registry over http on GET /metrics", async () => {
    const metrics = createMetrics();
    metrics.recordRun({ findings: [], durationSeconds: 1, now: 1_700_000_000 });
    const server = startMetricsServer(metrics.registry, 0); // ephemeral port
    try {
      await new Promise((resolve) => server.once("listening", resolve));
      const { port } = server.address();
      const res = await fetch(`http://127.0.0.1:${port}/metrics`);
      const body = await res.text();
      expect(res.status).toBe(200);
      expect(res.headers.get("content-type")).toContain("text/plain");
      expect(body).toContain("beholder_last_run_success 1");
    } finally {
      server.close();
    }
  });

  it("404s on any other path", async () => {
    const server = startMetricsServer(createMetrics().registry, 0);
    try {
      await new Promise((resolve) => server.once("listening", resolve));
      const { port } = server.address();
      const res = await fetch(`http://127.0.0.1:${port}/nope`);
      expect(res.status).toBe(404);
    } finally {
      server.close();
    }
  });
});
