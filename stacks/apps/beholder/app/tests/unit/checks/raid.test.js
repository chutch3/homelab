import { describe, expect, it } from "vitest";
import { raidCheck } from "../../../src/checks/raid.js";

describe("raidCheck", () => {
  it("is silent with no savings inflows", () => {
    expect(raidCheck({ savingsInflows: [] })).toBeNull();
    expect(raidCheck({ savingsInflows: undefined })).toBeNull();
  });

  it("raises with the exact total when money flows out of savings", () => {
    const finding = raidCheck({
      savingsInflows: [{ date: "2026-07-20", amount: 75000, payee: "Wealthfront" }],
    });
    expect(finding.check).toBe("raid");
    expect(finding.summary).toContain("$750.00");
    expect(finding.summary).toContain("1 transaction");
  });

  it("sums and lists every raid transaction", () => {
    const finding = raidCheck({
      savingsInflows: [
        { date: "2026-07-20", amount: 75000, payee: "Wealthfront" },
        { date: "2026-07-22", amount: 50000, payee: "Wealthfront" },
      ],
    });
    expect(finding.summary).toContain("$1,250.00");
    expect(finding.summary).toContain("2 transactions");
    expect(finding.detail).toContain("2026-07-20");
    expect(finding.detail).toContain("2026-07-22");
  });
});
