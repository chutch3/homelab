import { describe, expect, it } from "vitest";
import { scheduleCheck } from "../../../src/checks/schedule.js";

// Watched schedules arrive from the budget server; matching is by payee id.
describe("scheduleCheck", () => {
  it("provides structured comparisons for every mismatching payment", () => {
    const finding = scheduleCheck({
      recentTransactions: [{ date: "2026-09-01", amount: -125000, payeeId: "p" }],
      watched: [{ label: "Savings", payeeId: "p", expectedAmount: -110000 }],
    });
    expect(finding.comparisons).toEqual([
      { label: "Savings", date: "2026-09-01", expected: 110000, recorded: 125000, difference: 15000 },
    ]);
  });

  it("reports the observed payment difference without inferring autopay settings", () => {
    const finding = scheduleCheck({
      recentTransactions: [{ date: "2026-09-01", amount: -125000, payeeId: "p" }],
      watched: [{ payeeId: "p", expectedAmount: -110000, label: "Savings" }],
    });
    expect(finding).toEqual({
      check: "schedule",
      comparisons: [
        { label: "Savings", date: "2026-09-01", expected: 110000, recorded: 125000, difference: 15000 },
      ],
      postings: [{ date: "2026-09-01", amount: -125000, payeeId: "p" }],
    });
  });

  const watched = [
    { payeeId: "p-synchrony", expectedAmount: -20000, label: "Synchrony Credit Card - Furniture Bill" },
  ];

  it("is silent when the payment posts at the expected amount", () => {
    const txns = [{ date: "2026-07-24", amount: -20000, payeeId: "p-synchrony", payee: "Synchrony" }];
    expect(scheduleCheck({ recentTransactions: txns, watched })).toBeNull();
  });

  it("raises with schedule label, posted and expected amounts", () => {
    const txns = [{ date: "2026-07-24", amount: -11900, payeeId: "p-synchrony", payee: "Synchrony" }];
    const finding = scheduleCheck({ recentTransactions: txns, watched });
    expect(finding.check).toBe("schedule");
    expect(finding.comparisons).toEqual([
      {
        label: "Synchrony Credit Card - Furniture Bill",
        date: "2026-07-24",
        expected: 20000,
        recorded: 11900,
        difference: -8100,
      },
    ]);
    expect(finding.postings).toEqual(txns);
  });

  it("stays silent when another posting matches the expected amount (extra payments are fine)", () => {
    const txns = [
      { date: "2026-07-16", amount: -110000, payeeId: "p-wf", payee: "Wealthfront" },
      { date: "2026-07-20", amount: -50000, payeeId: "p-wf", payee: "Wealthfront" },
    ];
    const wfWatched = [{ payeeId: "p-wf", expectedAmount: -110000, label: "Savings schedule" }];
    expect(scheduleCheck({ recentTransactions: txns, watched: wfWatched })).toBeNull();
  });

  it("ignores payees without a watched schedule", () => {
    const txns = [{ date: "2026-07-24", amount: -11900, payeeId: "p-other", payee: "T-Mobile" }];
    expect(scheduleCheck({ recentTransactions: txns, watched })).toBeNull();
  });

  it("ignores inflows from a watched payee (refunds are not missed payments)", () => {
    const txns = [{ date: "2026-07-24", amount: 5000, payeeId: "p-synchrony", payee: "Synchrony" }];
    expect(scheduleCheck({ recentTransactions: txns, watched })).toBeNull();
  });

  it("is silent with no watched schedules", () => {
    const txns = [{ date: "2026-07-24", amount: -11900, payeeId: "p-synchrony", payee: "Synchrony" }];
    expect(scheduleCheck({ recentTransactions: txns, watched: [] })).toBeNull();
  });
});
