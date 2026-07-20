// Scheduler shell: run daily at BEHOLDER_RUN_AT (container TZ), or run
// immediately and exit with BEHOLDER_RUN_ONCE=1.
import { loadConfig } from "./config.js";
import { createLedger } from "./ledger.js";
import { sendMail } from "./mailer.js";
import { createMetrics, startMetricsServer } from "./metrics.js";
import { createReporter } from "./reporter.js";
import { runOnce } from "./run.js";
import { loadState, saveState } from "./state.js";
import { createSupervisor } from "./supervisor.js";

const config = loadConfig();
const metrics = createMetrics();
const reportFailure = createReporter({ metrics, sendMail, config });
const supervisor = createSupervisor({ proc: process, onFatal: reportFailure, log: console.warn });

async function execute() {
  const startedAt = Date.now();
  const ledger = createLedger({ ...config.actual, names: config.names, bestEffort: supervisor.bestEffort });
  const state = await loadState(config.statePath);
  const { findings } = await runOnce({ ledger, config, state });
  await saveState(config.statePath, state);
  metrics.recordRun({
    findings,
    durationSeconds: (Date.now() - startedAt) / 1000,
    now: Date.now() / 1000,
  });
  console.log(
    `[beholder] run complete: ${findings.length} finding(s)` +
      (findings.length ? ` -> alerted [${findings.map((f) => f.check).join(", ")}]` : " (quiet)"),
  );
}

function msUntilNextRun(runAt, now = new Date()) {
  const [h, m] = runAt.split(":").map(Number);
  const next = new Date(now);
  next.setHours(h, m, 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  return next - now;
}

for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => {
    console.log(`[beholder] ${signal} received, exiting`);
    process.exit(0);
  });
}

if (process.env.BEHOLDER_RUN_ONCE === "1") {
  execute()
    .then(() => process.exit(0))
    .catch(async (e) => {
      await reportFailure(e);
      process.exit(1);
    });
} else {
  startMetricsServer(metrics.registry);
  console.log(`[beholder] watching; daily run at ${config.runAt} (${process.env.TZ || "UTC"})`);
  console.log("[beholder] metrics on :9090/metrics");
  const loop = () => {
    setTimeout(async () => {
      try {
        await execute();
      } catch (e) {
        await reportFailure(e);
      }
      loop();
    }, msUntilNextRun(config.runAt));
  };
  loop();
}
