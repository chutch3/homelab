// Scheduler shell: run daily at BEHOLDER_RUN_AT (container TZ), or run
// immediately and exit with BEHOLDER_RUN_ONCE=1.
import { loadConfig } from "./config.js";
import { createLedger } from "./ledger.js";
import { sendMail } from "./mailer.js";
import { runOnce } from "./run.js";
import { loadState, saveState } from "./state.js";

const config = loadConfig();

async function execute() {
  const ledger = createLedger({ ...config.actual, names: config.names });
  const state = await loadState(config.statePath);
  const { findings } = await runOnce({ ledger, config, state });
  await saveState(config.statePath, state);
  console.log(
    `[beholder] run complete: ${findings.length} finding(s)` +
      (findings.length ? ` -> alerted [${findings.map((f) => f.check).join(", ")}]` : " (quiet)"),
  );
}

// A watchdog must not fail silently: a broken run is itself a finding.
async function reportFailure(error) {
  console.error("[beholder] run failed:", error.message);
  try {
    await sendMail({
      postalUrl: config.postalUrl,
      postalApiKey: config.postalApiKey,
      from: config.alertFrom,
      to: config.alertTo,
      subject: "beholder: run failed - the watchdog itself needs attention",
      body: `beholder could not complete its checks:\n\n${error.message}\n\nUntil this is fixed, nothing is being watched.`,
    });
  } catch (mailError) {
    console.error("[beholder] failure email also failed:", mailError.message);
  }
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
  console.log(`[beholder] watching; daily run at ${config.runAt} (${process.env.TZ || "UTC"})`);
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
