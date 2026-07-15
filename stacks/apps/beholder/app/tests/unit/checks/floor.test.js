import { describe, expect, it } from "vitest";
import { floorCheck } from "../../../src/checks/floor.js";

// Amounts are integer cents; card balances are negative when owed.
describe("floorCheck", () => {
  const cards = [
    { name: "Discover", balance: -152795 },
    { name: "Southwest", balance: -106597 },
    { name: "Amazon", balance: -3605 },
    { name: "Amex", balance: 0 },
  ];

  it("passes when checking covers what the cards owe", () => {
    expect(floorCheck({ checkingBalance: 308500, cards })).toBeNull();
  });

  it("passes when checking sits exactly at the floor", () => {
    expect(floorCheck({ checkingBalance: 262997, cards })).toBeNull();
  });

  it("fails with the exact shortfall when checking is below the floor", () => {
    const finding = floorCheck({ checkingBalance: 58501, cards });
    expect(finding.check).toBe("floor");
    // owed 262,997; held 58,501; short 204,496
    expect(finding.summary).toContain("$2,044.96");
    expect(finding.summary).toContain("$585.01");
    expect(finding.summary).toContain("$2,629.97");
  });

  it("lists only indebted cards in the detail", () => {
    const finding = floorCheck({ checkingBalance: 0, cards });
    expect(finding.detail).toContain("Discover");
    expect(finding.detail).not.toContain("Amex");
  });

  it("passes with no cards at all", () => {
    expect(floorCheck({ checkingBalance: 0, cards: [] })).toBeNull();
  });
});
