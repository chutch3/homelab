import { driftCheck } from "./checks/drift.js";
import { floorCheck } from "./checks/floor.js";
import { raidCheck } from "./checks/raid.js";
import { scheduleCheck } from "./checks/schedule.js";
import { uncategorizedCheck } from "./checks/uncategorized.js";
import { sendMail as defaultMailer } from "./mailer.js";

const SNAPSHOT_KEEP_DAYS = 60;
const DRIFT_LOOKBACK_DAYS = 30;

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function daysBetween(a, b) {
  return Math.abs(new Date(a) - new Date(b)) / 86400000;
}

// Snapshot nearest to `lookback` days ago (any history counts; drift needs
// a baseline, not a precise one).
function driftBaseline(snapshots, now) {
  if (snapshots.length === 0) return null;
  const target = new Date(now.getTime() - DRIFT_LOOKBACK_DAYS * 86400000);
  return snapshots.reduce(
    (best, s) =>
      !best || Math.abs(new Date(s.date) - target) < Math.abs(new Date(best.date) - target) ? s : best,
    null,
  );
}

// Event findings (raid, schedule) are deduped across runs via state so a
// wide sync-lag-tolerant lookback does not nag daily; condition findings
// (floor, drift) deliberately repeat until resolved.
const raidKey = (t) => `raid:${t.id ?? `${t.date}:${t.amount}:${t.payee}`}`;
const scheduleKey = (t) => `schedule:${t.payeeId}:${t.date}:${t.amount}`;
const uncategorizedKey = (t) => `uncat:${t.id ?? `${t.date}:${t.amount}:${t.payee}`}`;

function pruneAlerted(alerted, today) {
  const kept = {};
  for (const [key, date] of Object.entries(alerted ?? {})) {
    if (daysBetween(date, today) <= SNAPSHOT_KEEP_DAYS) kept[key] = date;
  }
  return kept;
}

export async function runOnce({ ledger, config, state, now = new Date(), mailer = defaultMailer }) {
  await ledger.open();
  try {
    const { checking, cards } = await ledger.accountBalances();
    const savingsInflows = await ledger.savingsInflows();
    const recentTransactions = await ledger.recentTransactions();
    const watchedSchedules = await ledger.watchedSchedules();
    const uncategorized = await ledger.uncategorizedTransactions();

    state.alerted = pruneAlerted(state.alerted, isoDate(now));
    const freshInflows = savingsInflows.filter((t) => !state.alerted[raidKey(t)]);
    const freshTransactions = recentTransactions.filter((t) => !state.alerted[scheduleKey(t)]);
    const freshUncategorized = uncategorized.filter((t) => !state.alerted[uncategorizedKey(t)]);

    const baseline = driftBaseline(state.snapshots ?? [], now);
    const findings = [
      floorCheck({ checkingBalance: checking, cards }),
      raidCheck({ savingsInflows: freshInflows }),
      baseline
        ? driftCheck({ cards, snapshotCards: baseline.cards, thresholdCents: config.driftThresholdCents })
        : null,
      scheduleCheck({ recentTransactions: freshTransactions, watched: watchedSchedules }),
      uncategorizedCheck({ uncategorized: freshUncategorized }),
    ].filter(Boolean);

    // Record today's snapshot, prune old ones.
    const today = isoDate(now);
    state.snapshots = (state.snapshots ?? [])
      .filter((s) => s.date !== today && daysBetween(s.date, today) <= SNAPSHOT_KEEP_DAYS)
      .concat([{ date: today, checking, cards: Object.fromEntries(cards.map((c) => [c.name, c.balance])) }])
      .sort((a, b) => a.date.localeCompare(b.date));

    if (findings.length > 0) {
      const body =
        `beholder saw ${findings.length} thing${findings.length > 1 ? "s" : ""} worth your attention:\n\n` +
        findings.map((f) => `* [${f.check}] ${f.summary}\n${f.detail}`).join("\n\n") +
        `\n\n(quiet by default: no email means all checks passed)`;
      await mailer({
        postalUrl: config.postalUrl,
        postalApiKey: config.postalApiKey,
        from: config.alertFrom,
        to: config.alertTo,
        subject: `beholder: ${findings.map((f) => f.check).join(", ")}`,
        body,
      });

      // Record event findings only after the alert went out, so a failed
      // send retries naturally on the next run.
      if (findings.some((f) => f.check === "raid")) {
        for (const t of freshInflows) state.alerted[raidKey(t)] = today;
      }
      for (const f of findings) {
        if (f.check === "schedule") {
          for (const t of f.postings) state.alerted[scheduleKey(t)] = today;
        }
        if (f.check === "uncategorized") {
          for (const t of f.transactions) state.alerted[uncategorizedKey(t)] = today;
        }
      }
    }

    return { findings };
  } finally {
    await ledger.close();
  }
}
