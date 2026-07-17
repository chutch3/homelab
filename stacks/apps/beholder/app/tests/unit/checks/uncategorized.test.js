import { describe, expect, it } from "vitest";
import { uncategorizedCheck } from "../../../src/checks/uncategorized.js";

describe("uncategorizedCheck", () => {
  it("is silent when everything is categorized", () => {
    expect(uncategorizedCheck({ uncategorized: [] })).toBeNull();
    expect(uncategorizedCheck({ uncategorized: undefined })).toBeNull();
  });

  it("raises with count and lists each transaction", () => {
    const finding = uncategorizedCheck({
      uncategorized: [
        { id: "t1", date: "2026-07-08", amount: -4599, payee: "Mystery Merchant", account: "Chase Checking" },
        { id: "t2", date: "2026-07-09", amount: -1250, payee: "Corner Store", account: "Discover" },
      ],
    });
    expect(finding.check).toBe("uncategorized");
    expect(finding.summary).toContain("2 transaction");
    expect(finding.detail).toContain("Mystery Merchant");
    expect(finding.detail).toContain("Corner Store");
    expect(finding.detail).toContain("-$45.99");
    expect(finding.detail).toContain("Discover");
  });
});
