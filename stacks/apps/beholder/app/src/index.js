// Scheduler shell: run daily at BEHOLDER_RUN_AT (container TZ), or run
// immediately and exit with BEHOLDER_RUN_ONCE=1.
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { loadConfig } from "./config.js";
import { createLedger } from "./ledger.js";
import { sendMail } from "./mailer.js";
import { createMetrics, startMetricsServer } from "./metrics.js";
import { createReporter } from "./reporter.js";
import { runOnce, scheduleDaily } from "./run.js";
import { loadState, saveState } from "./state.js";
import { createSupervisor } from "./supervisor.js";

const previewOutput = process.env.BEHOLDER_PREVIEW_OUTPUT;
const config = loadConfig({
  preview: Boolean(previewOutput),
  previewTo: process.env.BEHOLDER_PREVIEW_TO || "",
});
const metrics = createMetrics();
const reportFailure = createReporter({
  metrics,
  sendMail,
  config,
  now: () => Date.now() / 1000,
  log: console.error,
});
const supervisor = createSupervisor({ proc: process, onFatal: reportFailure, log: console.warn });

async function execute() {
  const startedAt = Date.now();
  const ledger = createLedger({ ...config.actual, names: config.names, bestEffort: supervisor.bestEffort });
  const state = await loadState(config.statePath);
  const { findings } = await runOnce({ ledger, config, state, now: new Date(), mailer: sendMail });
  await saveState(config.statePath, state);
  metrics.recordRun({
    findings,
    durationSeconds: (Date.now() - startedAt) / 1000,
    now: Date.now() / 1000,
  });
  console.log(
    `[beholder] run complete: ${findings.length} finding(s)` +
      (findings.length
        ? ` -> alerted [${findings.map((f) => f.check).join(", ")}]`
        : " -> daily update sent"),
  );
}

for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => {
    console.log(`[beholder] ${signal} received, exiting`);
    process.exit(0);
  });
}

if (previewOutput) {
  let cache;
  try {
    cache = await mkdtemp(join(tmpdir(), "beholder-preview-"));
    const ledger = createLedger({
      ...config.actual,
      dataDir: cache,
      names: config.names,
      bestEffort: supervisor.bestEffort,
    });
    const state = process.env.BEHOLDER_STATE_PATH ? await loadState(config.statePath) : { snapshots: [] };
    await runOnce({
      ledger,
      config,
      state,
      now: new Date(),
      mailer: async (message) => {
        await writeFile(previewOutput, message.html, { mode: 0o600 });
        console.log(`[beholder] preview saved: ${resolve(previewOutput)}`);
        if (config.alertTo.length) {
          await sendMail(message);
          console.log(`[beholder] preview emailed to ${config.alertTo.join(", ")}`);
        }
      },
    });
  } catch (error) {
    console.error(`[beholder] preview failed: ${error.message}`);
    process.exitCode = 1;
  } finally {
    if (cache) await rm(cache, { recursive: true, force: true });
  }
  process.exit(process.exitCode || 0);
} else if (process.env.BEHOLDER_RUN_ONCE === "1") {
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
  scheduleDaily({
    runAt: config.runAt,
    now: () => new Date(),
    schedule: setTimeout,
    execute,
    onError: reportFailure,
  });
}
