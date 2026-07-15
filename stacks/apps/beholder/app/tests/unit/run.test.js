import { describe, expect, it } from "vitest";
import { runOnce } from "../../src/run.js";

// Orchestrator unit tests: every owned seam (ledger, mailer) injected.
// The real boundaries are exercised in tests/integration/.

function fakeLedger(overrides = {}) {
  return {
    async open() {},
    async close() {},
    async accountBalances() {
      return {
        checking: 58501,
        cards: [
          { name: "Discover", balance: -152795 },
          { name: "Southwest", balance: -106597 },
        ],
        ...overrides.balances,
      };
    },
    async savingsInflows() {
      return overrides.savingsInflows ?? [];
    },
    async recentTransactions() {
      return overrides.recentTransactions ?? [];
    },
    async watchedSchedules() {
      return overrides.watchedSchedules ?? [];
    },
    async uncategorizedTransactions() {
      return overrides.uncategorized ?? [];
    },
  };
}

function fakeMailer() {
  const sent = [];
  const mailer = async (msg) => {
    sent.push(msg);
    return { message_id: "unit" };
  };
  return { mailer, sent };
}

const config = {
  postalUrl: "http://postal.unit.test",
  postalApiKey: "unit-key",
  alertFrom: "budget@unit.test",
  alertTo: ["a@unit.test", "b@unit.test"],
  driftThresholdCents: 20000,
};

describe("runOnce", () => {
  it("sends one email listing all findings when checks fail", async () => {
    const { mailer, sent } = fakeMailer();
    const result = await runOnce({
      ledger: fakeLedger(),
      config,
      state: { snapshots: [] },
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    expect(result.findings.map((f) => f.check)).toEqual(["floor"]);
    expect(sent.length).toBe(1);
    expect(sent[0].to).toEqual(["a@unit.test", "b@unit.test"]);
    expect(sent[0].from).toBe("budget@unit.test");
    expect(sent[0].subject).toContain("floor");
    expect(sent[0].body).toMatch(/below/i);
  });

  it("stays quiet when all checks pass", async () => {
    const { mailer, sent } = fakeMailer();
    const result = await runOnce({
      ledger: fakeLedger({ balances: { checking: 500000 } }),
      config,
      state: { snapshots: [] },
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    expect(result.findings).toEqual([]);
    expect(sent.length).toBe(0);
  });

  it("verifies postings against schedules read from the ledger", async () => {
    const { mailer, sent } = fakeMailer();
    const result = await runOnce({
      ledger: fakeLedger({
        balances: { checking: 500000 },
        watchedSchedules: [{ payeeId: "p-syn", expectedAmount: -20000, label: "Furniture Bill" }],
        recentTransactions: [{ date: "2026-07-24", amount: -11900, payeeId: "p-syn", payee: "Synchrony" }],
      }),
      config,
      state: { snapshots: [] },
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    expect(result.findings.map((f) => f.check)).toEqual(["schedule"]);
    expect(sent[0].body).toContain("Furniture Bill");
  });

  it("appends a snapshot each run and prunes older than 60 days", async () => {
    const { mailer } = fakeMailer();
    const state = {
      snapshots: [
        { date: "2026-04-01", checking: 1, cards: {} },
        { date: "2026-07-01", checking: 2, cards: { Discover: -100000 } },
      ],
    };
    await runOnce({
      ledger: fakeLedger({ balances: { checking: 500000 } }),
      config,
      state,
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    const dates = state.snapshots.map((s) => s.date);
    expect(dates).toContain("2026-07-10");
    expect(dates).toContain("2026-07-01");
    expect(dates).not.toContain("2026-04-01");
  });

  it("uses the snapshot nearest 30 days back for drift", async () => {
    const { mailer, sent } = fakeMailer();
    const state = {
      snapshots: [{ date: "2026-06-10", checking: 1, cards: { Discover: -50000 } }],
    };
    const result = await runOnce({
      ledger: fakeLedger({ balances: { checking: 500000, cards: [{ name: "Discover", balance: -152795 }] } }),
      config,
      state,
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    expect(result.findings.map((f) => f.check)).toEqual(["drift"]);
    expect(sent.length).toBe(1);
  });

  it("does not re-alert a raid transaction it has already reported", async () => {
    const { mailer, sent } = fakeMailer();
    const state = { snapshots: [] };
    const inflow = { id: "txn-raid-1", date: "2026-07-09", amount: 75000, payee: "Wealthfront" };
    const make = () => fakeLedger({ balances: { checking: 500000 }, savingsInflows: [inflow] });

    const first = await runOnce({
      ledger: make(),
      config,
      state,
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    expect(first.findings.map((f) => f.check)).toEqual(["raid"]);

    const second = await runOnce({
      ledger: make(),
      config,
      state,
      now: new Date("2026-07-11T07:00:00Z"),
      mailer,
    });
    expect(second.findings).toEqual([]);
    expect(sent.length).toBe(1);
  });

  it("does not re-alert a schedule anomaly it has already reported", async () => {
    const { mailer, sent } = fakeMailer();
    const state = { snapshots: [] };
    const make = () =>
      fakeLedger({
        balances: { checking: 500000 },
        watchedSchedules: [{ payeeId: "p-syn", expectedAmount: -20000, label: "Furniture Bill" }],
        recentTransactions: [{ date: "2026-07-24", amount: -11900, payeeId: "p-syn", payee: "Synchrony" }],
      });

    const first = await runOnce({
      ledger: make(),
      config,
      state,
      now: new Date("2026-07-25T07:00:00Z"),
      mailer,
    });
    expect(first.findings.map((f) => f.check)).toEqual(["schedule"]);

    const second = await runOnce({
      ledger: make(),
      config,
      state,
      now: new Date("2026-07-26T07:00:00Z"),
      mailer,
    });
    expect(second.findings).toEqual([]);
    expect(sent.length).toBe(1);
  });

  it("surfaces uncategorized transactions once and not again", async () => {
    const { mailer, sent } = fakeMailer();
    const state = { snapshots: [] };
    const txn = {
      id: "t-uncat-1",
      date: "2026-07-08",
      amount: -4599,
      payee: "Mystery Merchant",
      account: "Chase Checking",
    };
    const make = () => fakeLedger({ balances: { checking: 500000 }, uncategorized: [txn] });

    const first = await runOnce({
      ledger: make(),
      config,
      state,
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    expect(first.findings.map((f) => f.check)).toEqual(["uncategorized"]);
    expect(sent[0].body).toContain("Mystery Merchant");

    const second = await runOnce({
      ledger: make(),
      config,
      state,
      now: new Date("2026-07-11T07:00:00Z"),
      mailer,
    });
    expect(second.findings).toEqual([]);
    expect(sent.length).toBe(1);
  });

  it("closes the ledger even when a check path throws", async () => {
    let closed = false;
    const ledger = fakeLedger();
    ledger.close = async () => {
      closed = true;
    };
    ledger.accountBalances = async () => {
      throw new Error("boom");
    };
    await expect(
      runOnce({ ledger, config, state: { snapshots: [] }, mailer: fakeMailer().mailer }),
    ).rejects.toThrow("boom");
    expect(closed).toBe(true);
  });
});
