import { describe, expect, it } from "vitest";
import { raidCheck } from "../../../src/checks/raid.js";

describe("raidCheck", () => {
  it("provides structured transactions and their total for the email table", () => {
    const transactions = [{ date: "2026-09-01", amount: 2609, payee: "Interest" }];
    const finding = raidCheck({ savingsInflows: transactions });
    expect(finding.transactions).toEqual(transactions);
    expect(finding.total).toBe(2609);
  });

  it("describes category inflows without assuming a savings withdrawal", () => {
    const finding = raidCheck({ savingsInflows: [{ date: "2026-09-01", amount: 2609, payee: "Interest" }] });
    expect(finding).toEqual({
      check: "raid",
      total: 2609,
      transactions: [{ date: "2026-09-01", amount: 2609, payee: "Interest" }],
    });
  });

  it("is silent with no savings inflows", () => {
    expect(raidCheck({ savingsInflows: [] })).toBeNull();
    expect(raidCheck({ savingsInflows: undefined })).toBeNull();
  });

  it("raises with the exact total when money flows out of savings", () => {
    const finding = raidCheck({
      savingsInflows: [{ date: "2026-07-20", amount: 75000, payee: "Wealthfront" }],
    });
    expect(finding.check).toBe("raid");
    expect(finding.total).toBe(75000);
    expect(finding.transactions).toEqual([{ date: "2026-07-20", amount: 75000, payee: "Wealthfront" }]);
  });

  it("sums and lists every raid transaction", () => {
    const finding = raidCheck({
      savingsInflows: [
        { date: "2026-07-20", amount: 75000, payee: "Wealthfront" },
        { date: "2026-07-22", amount: 50000, payee: "Wealthfront" },
      ],
    });
    expect(finding.total).toBe(125000);
    expect(finding.transactions).toEqual([
      { date: "2026-07-20", amount: 75000, payee: "Wealthfront" },
      { date: "2026-07-22", amount: 50000, payee: "Wealthfront" },
    ]);
  });
});
