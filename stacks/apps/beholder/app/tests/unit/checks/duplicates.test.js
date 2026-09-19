import { describe, expect, it } from "vitest";
import { duplicatesCheck } from "../../../src/checks/duplicates.js";

const pending = {
  id: "p",
  importedId: "bank-p",
  accountId: "card",
  account: "Discover",
  merchant: "Coast Creamery",
  date: "2026-09-10",
  amount: -1260,
  cleared: false,
};
const posted = {
  ...pending,
  id: "f",
  importedId: "bank-f",
  merchant: "Coast Creamery Santa Rosa",
  amount: -1506,
  cleared: true,
};
const check = (transactions, windowDays = 3) =>
  duplicatesCheck({ transactions, windowDays, maxIncreasePercent: 30, holdMaxCents: 100 });
describe("duplicatesCheck", () => {
  it.each([
    [49, false],
    [50, true],
  ])("applies a configured %s percent limit at its boundary", (maxIncreasePercent, matches) => {
    const first = { ...pending, amount: -1000 };
    const final = { ...posted, amount: -1500 };
    expect(
      duplicatesCheck({ transactions: [first, final], windowDays: 3, maxIncreasePercent, holdMaxCents: 100 }),
    ).toEqual(matches ? { check: "duplicates", pairs: [{ pending: first, posted: final }] } : null);
  });
  it.each([
    [499, false],
    [500, true],
  ])("applies a configured %s cent hold limit at its boundary", (holdMaxCents, matches) => {
    const first = { ...pending, amount: -500 };
    const final = { ...posted, amount: -5000 };
    expect(
      duplicatesCheck({ transactions: [first, final], windowDays: 3, maxIncreasePercent: 30, holdMaxCents }),
    ).toEqual(matches ? { check: "duplicates", pairs: [{ pending: first, posted: final }] } : null);
  });
  it("allows disabling both amount matching rules with zero", () => {
    expect(
      duplicatesCheck({
        transactions: [{ ...pending, amount: -100 }, posted],
        windowDays: 3,
        maxIncreasePercent: 0,
        holdMaxCents: 0,
      }),
    ).toBeNull();
  });

  it("returns the two original entries for a likely tip adjustment", () => {
    expect(check([pending, posted])).toEqual({ check: "duplicates", pairs: [{ pending, posted }] });
  });
  it("matches a one-dollar hold without requiring a similar amount", () => {
    const hold = { ...pending, amount: -100 };
    const final = { ...posted, amount: -4285 };
    expect(check([hold, final])).toEqual({ check: "duplicates", pairs: [{ pending: hold, posted: final }] });
  });
  it.each([
    ["other account", { accountId: "other" }],
    ["same bank id", { importedId: "bank-p" }],
    ["missing bank id", { importedId: null }],
    ["still pending", { cleared: false }],
    ["refund", { amount: 1506 }],
    ["same amount", { amount: -1260 }],
    ["smaller final amount", { amount: -1200 }],
    ["increase over 30 percent", { amount: -1639 }],
    ["unrelated merchant", { merchant: "Coast Hardware" }],
    ["missing merchant", { merchant: "" }],
    ["invalid date", { date: "invalid" }],
    ["outside window", { date: "2026-09-14" }],
  ])("ignores %s", (_, changes) => {
    expect(check([pending, { ...posted, ...changes }])).toBeNull();
  });
  it("does not pair two cleared transactions", () => {
    expect(check([{ ...pending, cleared: true }, posted])).toBeNull();
  });
  it("requires an imported id on the pending entry", () => {
    expect(check([{ ...pending, importedId: null }, posted])).toBeNull();
  });
  it("ignores empty input", () => {
    expect(check([])).toBeNull();
  });
  it("includes the date-window boundary and respects a narrower override", () => {
    const final = { ...posted, date: "2026-09-13" };
    expect(check([pending, final], 3)).toEqual({ check: "duplicates", pairs: [{ pending, posted: final }] });
    expect(check([pending, final], 2)).toBeNull();
  });
  it("includes exactly a 30 percent increase", () => {
    const final = { ...posted, amount: -1638 };
    expect(check([pending, final])).toEqual({ check: "duplicates", pairs: [{ pending, posted: final }] });
  });
  it("normalizes case and punctuation", () => {
    const first = { ...pending, merchant: "JIMMY JOHN’S" };
    const final = { ...posted, merchant: "Jimmy Johns" };
    expect(check([first, final])).toEqual({
      check: "duplicates",
      pairs: [{ pending: first, posted: final }],
    });
  });
  it("does not treat Kroger and Kroger Fuel as the same merchant", () => {
    expect(
      check([
        { ...pending, merchant: "Kroger", amount: -100 },
        { ...posted, merchant: "Kroger Fuel" },
      ]),
    ).toBeNull();
  });
  it("skips one pending entry with multiple possible posted matches", () => {
    expect(check([pending, posted, { ...posted, id: "f2", importedId: "bank-f2" }])).toBeNull();
  });
  it("skips multiple pending entries competing for one posted match", () => {
    expect(check([pending, { ...pending, id: "p2", importedId: "bank-p2" }, posted])).toBeNull();
  });
});
