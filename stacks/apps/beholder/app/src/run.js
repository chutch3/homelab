import { driftCheck } from "./checks/drift.js";
import { duplicatesCheck } from "./checks/duplicates.js";
import { floorCheck } from "./checks/floor.js";
import { raidCheck } from "./checks/raid.js";
import { scheduleCheck } from "./checks/schedule.js";
import { uncategorizedCheck } from "./checks/uncategorized.js";
import {
  driftBaseline,
  pruneNotifications,
  recordNotifications,
  recordSnapshot,
  unnotifiedTransactions,
} from "./history.js";
import { cardGrowth, categoryActivity, categoryTotals } from "./money.js";

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

export async function runOnce({ ledger, config, state, now, mailer, renderEmail }) {
  await ledger.open();
  try {
    const { checking, cards } = await ledger.accountBalances();
    const reportDate = [
      now.getFullYear(),
      String(now.getMonth() + 1).padStart(2, "0"),
      String(now.getDate()).padStart(2, "0"),
    ].join("-");
    const categories = await ledger.monthlyCategories(reportDate.slice(0, 7));
    const savingsInflows = await ledger.savingsInflows();
    const recentTransactions = await ledger.recentTransactions();
    const watchedSchedules = await ledger.watchedSchedules();
    const uncategorized = await ledger.uncategorizedTransactions();
    const duplicateSince = new Date(now.getTime() - config.duplicates.lookbackDays * 86400000);
    const duplicateTransactions = await ledger.duplicateTransactions(isoDate(duplicateSince));

    const today = isoDate(now);
    state.alerted = pruneNotifications(state.alerted, today);
    const freshInflows = unnotifiedTransactions(savingsInflows, "raid", state.alerted);
    const freshTransactions = unnotifiedTransactions(recentTransactions, "schedule", state.alerted);
    const freshUncategorized = unnotifiedTransactions(uncategorized, "uncategorized", state.alerted);

    const baseline = driftBaseline(state.snapshots ?? [], now);
    const findings = [
      floorCheck({ checkingBalance: checking, cards }),
      raidCheck({ savingsInflows: freshInflows }),
      baseline
        ? driftCheck({ cards, snapshotCards: baseline.cards, thresholdCents: config.driftThresholdCents })
        : null,
      scheduleCheck({ recentTransactions: freshTransactions, watched: watchedSchedules }),
      uncategorizedCheck({ uncategorized: freshUncategorized }),
      duplicatesCheck({
        transactions: duplicateTransactions,
        windowDays: config.duplicates.windowDays,
        maxIncreasePercent: config.duplicates.maxIncreasePercent,
        holdMaxCents: config.duplicates.holdMaxCents,
      }),
    ].filter(Boolean);

    state.snapshots = recordSnapshot(state.snapshots, { date: today, checking, cards });

    const report = await renderEmail({
      date: reportDate,
      categories: categories.map((category) => ({ ...category, activity: categoryActivity(category) })),
      checking,
      cards,
      baseline,
      findings,
      uncategorized,
      budgetUrl: config.budgetUrl,
      categoryTotals: categoryTotals(categories),
      cardChanges:
        baseline && findings.some((finding) => finding.check === "drift")
          ? cardGrowth(cards, baseline.cards, config.driftThresholdCents)
          : [],
      uncategorizedTotals: uncategorized.reduce(
        (totals, transaction) => ({
          spending: totals.spending - Math.min(transaction.amount, 0),
          inflows: totals.inflows + Math.max(transaction.amount, 0),
        }),
        { spending: 0, inflows: 0 },
      ),
    });
    await mailer({
      postalUrl: config.postalUrl,
      postalApiKey: config.postalApiKey,
      from: config.alertFrom,
      to: config.alertTo,
      subject: report.subject,
      body: report.text,
      html: report.html,
    });

    // A failed send must leave event findings eligible for the next run.
    state.alerted = recordNotifications(state.alerted, findings, today);

    return { findings };
  } finally {
    await ledger.close();
  }
}
