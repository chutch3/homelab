import { describe, expect, it } from "vitest";
import { runOnce as executeRun } from "../../src/run.js";

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
    async monthlyCategories() {
      return [];
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
    async duplicateTransactions(since) {
      if (overrides.readDuplicate) return overrides.readDuplicate(since);
      return overrides.duplicates ?? [];
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
  duplicates: { lookbackDays: 90, windowDays: 3, maxIncreasePercent: 30, holdMaxCents: 100 },
  budgetUrl: "https://budget.unit.test/",
};

// Unit defaults inject the owned renderer seam; the existing e2e suite verifies delivered content.
const runOnce = (options) =>
  executeRun({
    renderEmail: async () => ({ subject: "Budget", text: "Plain report", html: "<p>Report</p>" }),
    ...options,
  });

function fakeRenderer() {
  const reports = [];
  return {
    reports,
    renderEmail: async (report) => {
      reports.push(report);
      return { subject: "Budget", text: "Plain report", html: "<p>Report</p>" };
    },
  };
}

describe("runOnce", () => {
  it("passes the complete report to the injected renderer and delivers its result", async () => {
    const categories = [{ name: "Food", balance: 500, spent: -100, budgeted: 400 }];
    const ledger = fakeLedger({ balances: { checking: 500000 } });
    ledger.monthlyCategories = async () => categories;
    const reports = [];
    const { mailer, sent } = fakeMailer();
    await runOnce({
      ledger,
      config,
      state: { snapshots: [] },
      now: new Date(2026, 8, 10, 7),
      mailer,
      renderEmail: async (report) => {
        reports.push(report);
        return { subject: "Rendered subject", text: "Rendered text", html: "<p>Rendered HTML</p>" };
      },
    });
    expect(reports).toEqual([
      {
        date: "2026-09-10",
        categories: [
          {
            name: "Food",
            balance: 500,
            spent: -100,
            budgeted: 400,
            activity: {
              available: 600,
              spent: 100,
              inflow: 0,
              percentage: 17,
              barPercent: 17,
            },
          },
        ],
        checking: 500000,
        cards: [
          { name: "Discover", balance: -152795 },
          { name: "Southwest", balance: -106597 },
        ],
        baseline: null,
        findings: [],
        uncategorized: [],
        budgetUrl: config.budgetUrl,
        categoryTotals: { budgeted: 400, spent: 100, percentage: 25, barPercent: 25 },
        cardChanges: [],
        uncategorizedTotals: { spending: 0, inflows: 0 },
      },
    ]);
    expect(sent).toEqual([
      {
        postalUrl: config.postalUrl,
        postalApiKey: config.postalApiKey,
        from: config.alertFrom,
        to: config.alertTo,
        subject: "Rendered subject",
        body: "Rendered text",
        html: "<p>Rendered HTML</p>",
      },
    ]);
  });

  it("passes numeric transaction totals and category activity without mutating ledger data", async () => {
    const categories = [
      { name: "Zero", balance: 0 },
      { name: "<Food>", balance: -2500, spent: -12500 },
    ];
    const before = structuredClone(categories);
    const transactions = [
      { id: "purchase", date: "2026-09-09", payee: "Shop", account: "Card", amount: -1000 },
      { id: "refund", date: "2026-09-09", payee: "Refund", account: "Card", amount: 500 },
    ];
    const ledger = fakeLedger({ uncategorized: transactions });
    ledger.monthlyCategories = async () => categories;
    const renderer = fakeRenderer();
    await runOnce({
      ledger,
      config,
      state: { snapshots: [] },
      now: new Date(2026, 8, 10, 7),
      mailer: fakeMailer().mailer,
      renderEmail: renderer.renderEmail,
    });
    expect(renderer.reports[0].uncategorizedTotals).toEqual({ spending: 1000, inflows: 500 });
    expect(renderer.reports[0].uncategorized).toEqual(transactions);
    expect(renderer.reports[0].categories).toEqual([
      { name: "Zero", balance: 0, activity: null },
      {
        name: "<Food>",
        balance: -2500,
        spent: -12500,
        activity: {
          available: 10000,
          spent: 12500,
          inflow: 0,
          percentage: 125,
          barPercent: 100,
        },
      },
    ]);
    expect(categories).toEqual(before);
  });

  it("closes the ledger without sending or acknowledging events when rendering fails", async () => {
    const ledger = fakeLedger({
      savingsInflows: [{ id: "raid", date: "2026-09-09", amount: 1000, payee: "Savings" }],
    });
    let closed = false;
    ledger.close = async () => {
      closed = true;
    };
    const state = { snapshots: [], alerted: {} };
    const { mailer, sent } = fakeMailer();
    const failure = new Error("template failed");
    await expect(
      runOnce({
        ledger,
        config,
        state,
        now: new Date(2026, 8, 10, 7),
        mailer,
        renderEmail: async () => {
          throw failure;
        },
      }),
    ).rejects.toBe(failure);
    expect(closed).toBe(true);
    expect(sent).toEqual([]);
    expect(state.alerted).toEqual({});
  });

  it("reads the configured duplicate lookback and closes on read failure", async () => {
    const dates = [];
    const ledger = fakeLedger({
      readDuplicate: async (since) => {
        dates.push(since);
        throw new Error("read failed");
      },
    });
    let closed = false;
    ledger.close = async () => {
      closed = true;
    };
    const { mailer, sent } = fakeMailer();
    await expect(
      runOnce({
        ledger,
        config: { ...config, duplicates: { lookbackDays: 30, windowDays: 2 } },
        state: {},
        now: new Date("2026-09-18T07:00:00Z"),
        mailer,
      }),
    ).rejects.toThrow("read failed");
    expect(dates).toEqual(["2026-08-19"]);
    expect(closed).toBe(true);
    expect(sent).toEqual([]);
  });

  it("passes the local calendar month to the ledger", async () => {
    const months = [];
    const ledger = fakeLedger();
    ledger.monthlyCategories = async (month) => {
      months.push(month);
      return [];
    };
    await runOnce({
      ledger,
      config,
      state: { snapshots: [] },
      now: new Date(2026, 0, 1, 0, 15),
      mailer: fakeMailer().mailer,
    });
    expect(months).toEqual(["2026-01"]);
  });

  it("does not send or mark events when reading monthly categories fails", async () => {
    const ledger = fakeLedger();
    let closed = false;
    ledger.monthlyCategories = async () => {
      throw new Error("budget unavailable");
    };
    ledger.close = async () => {
      closed = true;
    };
    const { mailer, sent } = fakeMailer();
    const state = { snapshots: [], alerted: {} };
    await expect(
      runOnce({ ledger, config, state, now: new Date("2026-09-10T07:00:00Z"), mailer }),
    ).rejects.toThrow("budget unavailable");
    expect(sent).toEqual([]);
    expect(state).toEqual({ snapshots: [], alerted: {} });
    expect(closed).toBe(true);
  });

  it("does not mark event findings when mail delivery fails", async () => {
    const ledger = fakeLedger({
      savingsInflows: [{ id: "raid-1", date: "2026-09-09", amount: 1000, payee: "Savings" }],
    });
    const state = { snapshots: [], alerted: {} };
    await expect(
      runOnce({
        ledger,
        config,
        state,
        now: new Date("2026-09-10T07:00:00Z"),
        mailer: async () => {
          throw new Error("mail rejected");
        },
      }),
    ).rejects.toThrow("mail rejected");
    expect(state.alerted).toEqual({});
  });

  it("passes all findings to the renderer and sends one email when checks fail", async () => {
    const { mailer, sent } = fakeMailer();
    const renderer = fakeRenderer();
    const result = await runOnce({
      ledger: fakeLedger({
        savingsInflows: [{ id: "raid", date: "2026-07-09", amount: 75000, payee: "Savings" }],
        watchedSchedules: [{ payeeId: "bill", expectedAmount: -20000, label: "Furniture" }],
        recentTransactions: [{ date: "2026-07-09", amount: -11900, payeeId: "bill" }],
        uncategorized: [
          { id: "uncat", date: "2026-07-09", amount: -4599, payee: "Mystery", account: "Discover" },
        ],
      }),
      config,
      state: { snapshots: [{ date: "2026-06-10", cards: { Discover: -50000 } }] },
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
      renderEmail: renderer.renderEmail,
    });
    expect(result.findings.map((f) => f.check)).toEqual([
      "floor",
      "raid",
      "drift",
      "schedule",
      "uncategorized",
    ]);
    expect(sent.length).toBe(1);
    expect(sent[0].to).toEqual(["a@unit.test", "b@unit.test"]);
    expect(sent[0].from).toBe("budget@unit.test");

    expect(renderer.reports[0].findings).toEqual(result.findings);
  });

  it("sends a daily update when all checks pass", async () => {
    const { mailer, sent } = fakeMailer();
    const result = await runOnce({
      ledger: fakeLedger({ balances: { checking: 500000 } }),
      config,
      state: { snapshots: [] },
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
    });
    expect(result.findings).toEqual([]);
    expect(sent.length).toBe(1);
  });

  it("verifies postings against schedules read from the ledger", async () => {
    const { mailer } = fakeMailer();
    const renderer = fakeRenderer();
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
      renderEmail: renderer.renderEmail,
    });
    expect(result.findings.map((f) => f.check)).toEqual(["schedule"]);
    expect(renderer.reports[0].findings[0].comparisons[0].label).toBe("Furniture Bill");
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
    const renderer = fakeRenderer();
    const state = {
      snapshots: [
        { date: "2026-06-01", checking: 1, cards: { Discover: -152795 } },
        { date: "2026-06-11", checking: 2, cards: { Discover: -50000 } },
        { date: "2026-06-20", checking: 3, cards: { Discover: -152795 } },
      ],
    };
    const result = await runOnce({
      ledger: fakeLedger({ balances: { checking: 500000, cards: [{ name: "Discover", balance: -152795 }] } }),
      config,
      state,
      now: new Date("2026-07-10T07:00:00Z"),
      mailer,
      renderEmail: renderer.renderEmail,
    });
    expect(result.findings.map((f) => f.check)).toEqual(["drift"]);
    expect(sent.length).toBe(1);
    expect(renderer.reports[0].baseline).toEqual({
      date: "2026-06-11",
      checking: 2,
      cards: { Discover: -50000 },
    });
    const then = -50000;
    expect(renderer.reports[0].cardChanges).toEqual([
      { name: "Discover", growth: 102795, then, now: -152795 },
    ]);
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
    expect(sent.length).toBe(2);
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
    expect(sent.length).toBe(2);
  });

  it("counts uncategorized findings once but keeps unresolved context in daily emails", async () => {
    const { mailer, sent } = fakeMailer();
    const renderer = fakeRenderer();
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
      renderEmail: renderer.renderEmail,
    });
    expect(first.findings.map((f) => f.check)).toEqual(["uncategorized"]);

    const second = await runOnce({
      ledger: make(),
      config,
      state,
      now: new Date("2026-07-11T07:00:00Z"),
      mailer,
      renderEmail: renderer.renderEmail,
    });
    expect(second.findings).toEqual([]);
    expect(sent.length).toBe(2);
    expect(renderer.reports.map((report) => report.uncategorized)).toEqual([[txn], [txn]]);
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
