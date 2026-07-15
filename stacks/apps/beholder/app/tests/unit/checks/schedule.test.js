import { describe, expect, it } from "vitest";
import { scheduleCheck } from "../../../src/checks/schedule.js";

// Watched schedules arrive from the budget server; matching is by payee id.
describe("scheduleCheck", () => {
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
    expect(finding.summary).toContain("Synchrony Credit Card - Furniture Bill");
    expect(finding.summary).toContain("$119.00");
    expect(finding.summary).toContain("$200.00");
    expect(finding.summary).toContain("2026-07-24");
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
