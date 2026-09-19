// Prometheus metrics for the watchdog. In daemon mode a tiny /metrics server runs
// alongside the scheduler so the monitoring stack can scrape run health — most
// importantly beholder_last_run_timestamp_seconds, which tells you it's still running
// even when everything is healthy and no alert email is sent.
import http from "node:http";

import { Counter, collectDefaultMetrics, Gauge, Registry } from "prom-client";

const CHECKS = ["floor", "raid", "drift", "schedule", "uncategorized", "duplicates"];

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
  const instruments = { lastRunTimestamp, lastRunSuccess, runDuration, runsTotal, findings };
  const recorder = createMetricsRecorder({
    set(name, value, labels) {
      if (labels) instruments[name].set(labels, value);
      else instruments[name].set(value);
    },
    increment(name, labels) {
      instruments[name].inc(labels);
    },
  });
  return { registry, ...recorder };
}

// Owned sink contract keeps recording decisions independent of Prometheus.
export function createMetricsRecorder(sink) {
  for (const check of CHECKS) sink.set("findings", 0, { check });
  return {
    recordRun({ findings, durationSeconds, now }) {
      sink.set("lastRunTimestamp", now);
      sink.set("lastRunSuccess", 1);
      sink.set("runDuration", durationSeconds);
      sink.increment("runsTotal", { outcome: "success" });
      for (const check of CHECKS)
        sink.set("findings", findings.filter((finding) => finding.check === check).length, { check });
    },
    recordFailure({ now }) {
      sink.set("lastRunTimestamp", now);
      sink.set("lastRunSuccess", 0);
      sink.increment("runsTotal", { outcome: "failure" });
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
