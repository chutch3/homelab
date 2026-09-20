import { describe, expect, it } from "vitest";
import {
  driftBaseline,
  pruneNotifications,
  recordNotifications,
  recordSnapshot,
  unnotifiedTransactions,
} from "../../src/history.js";

const today = "2026-09-20";
const now = new Date(`${today}T07:00:00Z`);

describe("driftBaseline", () => {
  it("uses the snapshot nearest 30 days ago without requiring a full month of history", () => {
    const snapshots = [
      { date: "2026-08-01", cards: { Card: -100 } },
      { date: "2026-08-22", cards: { Card: -200 } },
      { date: "2026-09-19", cards: { Card: -300 } },
    ];
    expect(driftBaseline(snapshots, now)).toBe(snapshots[1]);
    expect(driftBaseline([snapshots[2]], now)).toBe(snapshots[2]);
  });

  it("returns no baseline for empty history", () => {
    expect(driftBaseline([], now)).toBeNull();
    expect(driftBaseline(undefined, now)).toBeNull();
  });

  it("preserves the first snapshot on an exact tie", () => {
    const first = { date: "2026-08-20", cards: {} };
    const second = { date: "2026-08-22", cards: {} };
    expect(driftBaseline([first, second], new Date(`${today}T00:00:00Z`))).toBe(first);
  });
});

describe("pruneNotifications", () => {
  it("keeps the 60-day boundary and discards older acknowledgements without mutating history", () => {
    const alerted = { old: "2026-07-21", boundary: "2026-07-22", recent: "2026-09-19" };
    expect(pruneNotifications(alerted, today)).toEqual({ boundary: "2026-07-22", recent: "2026-09-19" });
    expect(alerted).toEqual({ old: "2026-07-21", boundary: "2026-07-22", recent: "2026-09-19" });
    expect(pruneNotifications(undefined, today)).toEqual({});
  });
});

describe("unnotifiedTransactions", () => {
  it.each([
    ["raid", "raid:saved", "raid:2026-09-19:100:Shop"],
    ["uncategorized", "uncat:saved", "uncat:2026-09-19:100:Shop"],
  ])("recognizes persisted IDs and fallback keys for %s", (check, idKey, fallbackKey) => {
    const saved = { id: "saved", date: "2026-09-19", amount: 100, payee: "Shop" };
    const fallback = { date: "2026-09-19", amount: 100, payee: "Shop" };
    const fresh = { id: "fresh", date: "2026-09-19", amount: 100, payee: "Shop" };
    const transactions = [saved, fallback, fresh];
    expect(unnotifiedTransactions(transactions, check, { [idKey]: today, [fallbackKey]: today })).toEqual([
      fresh,
    ]);
    expect(transactions).toEqual([saved, fallback, fresh]);
  });

  it("keys scheduled payments by payee, date, and amount rather than transaction ID", () => {
    const saved = { id: "new-id", payeeId: "bill", date: "2026-09-19", amount: -100 };
    const changed = { ...saved, amount: -200 };
    expect(
      unnotifiedTransactions([saved, changed], "schedule", {
        "schedule:bill:2026-09-19:-100": today,
      }),
    ).toEqual([changed]);
  });

  it("does not suppress one kind of event because another kind was acknowledged", () => {
    const transaction = { id: "same" };
    expect(unnotifiedTransactions([transaction], "raid", { "uncat:same": today })).toEqual([transaction]);
    expect(unnotifiedTransactions([], "raid", {})).toEqual([]);
  });
});

describe("recordSnapshot", () => {
  it("replaces today's snapshot, keeps 60 days, and sorts without mutating earlier snapshots", () => {
    const snapshots = [
      { date: today, checking: 1, cards: {} },
      { date: "2026-09-19", checking: 2, cards: {} },
      { date: "2026-07-21", checking: 3, cards: {} },
      { date: "2026-07-22", checking: 4, cards: {} },
    ];
    const before = structuredClone(snapshots);
    expect(
      recordSnapshot(snapshots, { date: today, checking: 500, cards: [{ name: "Card", balance: -100 }] }),
    ).toEqual([snapshots[3], snapshots[1], { date: today, checking: 500, cards: { Card: -100 } }]);
    expect(snapshots).toEqual(before);
  });

  it("starts history with the supplied date and balances", () => {
    expect(recordSnapshot(undefined, { date: today, checking: 0, cards: [] })).toEqual([
      { date: today, checking: 0, cards: {} },
    ]);
  });
});

describe("recordNotifications", () => {
  it("acknowledges only event transactions actually included in findings", () => {
    const raid = { id: "raid-1" };
    const uncategorized = { date: "2026-09-19", amount: -500, payee: "Shop" };
    const posting = { payeeId: "bill", date: "2026-09-19", amount: -200 };
    const alerted = { existing: "2026-09-18" };
    const updated = recordNotifications(
      alerted,
      [
        { check: "raid", transactions: [raid] },
        { check: "schedule", postings: [posting] },
        { check: "uncategorized", transactions: [uncategorized] },
        { check: "floor" },
        { check: "drift" },
        { check: "duplicates" },
      ],
      today,
    );
    expect(updated).toEqual({
      existing: "2026-09-18",
      "raid:raid-1": today,
      "schedule:bill:2026-09-19:-200": today,
      "uncat:2026-09-19:-500:Shop": today,
    });
    expect(alerted).toEqual({ existing: "2026-09-18" });
    expect(unnotifiedTransactions([raid], "raid", updated)).toEqual([]);
    expect(unnotifiedTransactions([posting], "schedule", updated)).toEqual([]);
    expect(unnotifiedTransactions([uncategorized], "uncategorized", updated)).toEqual([]);
  });

  it("leaves acknowledgements unchanged when no event was reported", () => {
    expect(recordNotifications({ existing: "2026-09-18" }, [], today)).toEqual({ existing: "2026-09-18" });
  });
});
