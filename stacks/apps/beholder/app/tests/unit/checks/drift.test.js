import { describe, expect, it } from "vitest";
import { driftCheck } from "../../../src/checks/drift.js";

describe("driftCheck", () => {
  it("is silent when debt is stable or shrinking", () => {
    expect(
      driftCheck({
        cards: [{ name: "Discover", balance: -100000 }],
        snapshotCards: { Discover: -120000 },
        thresholdCents: 20000,
      }),
    ).toBeNull();
  });

  it("is silent when growth stays within the threshold", () => {
    expect(
      driftCheck({
        cards: [{ name: "Discover", balance: -119999 }],
        snapshotCards: { Discover: -100000 },
        thresholdCents: 20000,
      }),
    ).toBeNull();
  });

  it("raises with exact growth figures past the threshold", () => {
    const finding = driftCheck({
      cards: [{ name: "Discover", balance: -190000 }],
      snapshotCards: { Discover: -100000 },
      thresholdCents: 20000,
    });
    expect(finding.check).toBe("drift");
    expect(finding.summary).toContain("Discover");
    expect(finding.summary).toContain("$900.00");
    expect(finding.summary).toContain("-$1,000.00");
    expect(finding.summary).toContain("-$1,900.00");
  });

  it("reports every drifting card in one finding", () => {
    const finding = driftCheck({
      cards: [
        { name: "Discover", balance: -190000 },
        { name: "Southwest", balance: -80000 },
      ],
      snapshotCards: { Discover: -100000, Southwest: -30000 },
      thresholdCents: 20000,
    });
    expect(finding.summary).toContain("Discover");
    expect(finding.summary).toContain("Southwest");
  });

  it("ignores cards missing from the snapshot", () => {
    expect(
      driftCheck({ cards: [{ name: "New", balance: -500000 }], snapshotCards: {}, thresholdCents: 20000 }),
    ).toBeNull();
  });
});
