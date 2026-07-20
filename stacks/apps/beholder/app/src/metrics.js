// Prometheus metrics for the watchdog. In daemon mode a tiny /metrics server runs
// alongside the scheduler so the monitoring stack can scrape run health — most
// importantly beholder_last_run_timestamp_seconds, which tells you it's still running
// even when everything is healthy and no alert email is sent.
import http from "node:http";

import { Counter, collectDefaultMetrics, Gauge, Registry } from "prom-client";

const CHECKS = ["floor", "raid", "drift", "schedule", "uncategorized"];

export function createMetrics() {
  const registry = new Registry();
  collectDefaultMetrics({ register: registry });

  const lastRunTimestamp = new Gauge({
    name: "beholder_last_run_timestamp_seconds",
    help: "Unix time of the last completed run (success or failure)",
    registers: [registry],
  });
  const lastRunSuccess = new Gauge({
    name: "beholder_last_run_success",
    help: "1 if the last run completed, 0 if it failed",
    registers: [registry],
  });
  const runDuration = new Gauge({
    name: "beholder_run_duration_seconds",
    help: "Duration of the last run in seconds",
    registers: [registry],
  });
  const runsTotal = new Counter({
    name: "beholder_runs_total",
    help: "Total runs by outcome",
    labelNames: ["outcome"],
    registers: [registry],
  });
  const findings = new Gauge({
    name: "beholder_findings",
    help: "Findings from the last run, by check",
    labelNames: ["check"],
    registers: [registry],
  });
  // Emit a zero series per check up front, so the metric exists before the first run.
  for (const check of CHECKS) findings.set({ check }, 0);

  return {
    registry,

    recordRun({ findings: runFindings, durationSeconds, now }) {
      lastRunTimestamp.set(now);
      lastRunSuccess.set(1);
      runDuration.set(durationSeconds);
      runsTotal.inc({ outcome: "success" });
      const counts = Object.fromEntries(CHECKS.map((c) => [c, 0]));
      for (const f of runFindings) {
        if (f.check in counts) counts[f.check] += 1;
      }
      for (const check of CHECKS) findings.set({ check }, counts[check]);
    },

    recordFailure({ now }) {
      lastRunTimestamp.set(now);
      lastRunSuccess.set(0);
      runsTotal.inc({ outcome: "failure" });
    },
  };
}

export function startMetricsServer(registry, port = 9090) {
  const server = http.createServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/metrics") {
      res.setHeader("Content-Type", registry.contentType);
      res.end(await registry.metrics());
    } else {
      res.statusCode = 404;
      res.end("not found");
    }
  });
  server.listen(port);
  return server;
}
