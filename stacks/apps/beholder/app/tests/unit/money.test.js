import { describe, expect, it } from "vitest";
import { cardCoverage, cardGrowth, categoryActivity, categoryTotals, fmt } from "../../src/money.js";

describe("fmt", () => {
  it("formats cents as dollars with two decimals", () => {
    expect(fmt(12030)).toBe("$120.30");
  });

  it("keeps the sign in front of the dollar symbol", () => {
    expect(fmt(-110000)).toBe("-$1,100.00");
  });

  it("adds thousands separators", () => {
    expect(fmt(406595)).toBe("$4,065.95");
  });

  it("handles zero and sub-dollar amounts", () => {
    expect(fmt(0)).toBe("$0.00");
    expect(fmt(-99)).toBe("-$0.99");
  });
});

describe("cardCoverage", () => {
  it("ignores card credits when calculating debt, headroom and coverage", () => {
    expect(cardCoverage(5000, [{ balance: -10000 }, { balance: 2500 }])).toEqual({
      owed: 10000,
      headroom: -5000,
      percent: 50,
    });
  });
  it("preserves negative checking when there are no cards", () => {
    expect(cardCoverage(-1000, [])).toEqual({ owed: 0, headroom: -1000, percent: null });
  });
  it.each([
    [0, 0],
    [-1000, 0],
    [10000, 100],
    [20000, 100],
  ])("bounds visual coverage for checking %s", (checking, percent) => {
    expect(cardCoverage(checking, [{ balance: -10000 }])).toEqual({
      owed: 10000,
      headroom: checking - 10000,
      percent,
    });
  });
});

describe("cardGrowth", () => {
  it("returns only cards exceeding the supplied threshold with exact amounts", () => {
    const then = -100000;
    expect(
      cardGrowth(
        [
          { name: "Above", balance: -130001 },
          { name: "At", balance: -130000 },
          { name: "Below", balance: -100100 },
          { name: "New", balance: -999999 },
        ],
        { Above: -100000, At: -100000, Below: -100000 },
        30000,
      ),
    ).toEqual([{ name: "Above", growth: 30001, then, now: -130001 }]);
  });
  it("returns no growth for empty or shrinking balances", () => {
    expect(cardGrowth([], {}, 20000)).toEqual([]);
    expect(cardGrowth([{ name: "Card", balance: -5000 }], { Card: -10000 }, 0)).toEqual([]);
  });
});

describe("categoryActivity", () => {
  it.each([
    [7500, -2500, { available: 10000, spent: 2500, inflow: 0, percentage: 25, barPercent: 25 }],
    [-2500, -12500, { available: 10000, spent: 12500, inflow: 0, percentage: 125, barPercent: 100 }],
    [0, 0, { available: 0, spent: 0, inflow: 0, percentage: null, barPercent: 0 }],
    [-1000, -1000, { available: 0, spent: 1000, inflow: 0, percentage: null, barPercent: 100 }],
    [12000, 2000, { available: 10000, spent: 0, inflow: 2000, percentage: 0, barPercent: 0 }],
  ])("calculates activity for balance %s and net spending %s", (balance, spent, expected) => {
    expect(categoryActivity({ balance, spent })).toEqual(expected);
  });
  it.each([undefined, NaN, Infinity])("omits unavailable activity (%s)", (spent) => {
    expect(categoryActivity({ balance: 1000, spent })).toBeNull();
  });
});

describe("categoryTotals", () => {
  it("compares combined spending with this month's budgets, excluding carryover", () => {
    const categories = [
      { budgeted: 20000, balance: 27500, spent: -2500 },
      { budgeted: 10000, balance: 2500, spent: -7500 },
    ];
    const before = structuredClone(categories);
    expect(categoryTotals(categories)).toEqual({
      budgeted: 30000,
      spent: 10000,
      percentage: 33,
      barPercent: 33,
    });
    expect(categories).toEqual(before);
  });

  it("keeps net inflows in one category from hiding spending in another", () => {
    expect(
      categoryTotals([
        { budgeted: 10000, spent: -2500 },
        { budgeted: 5000, spent: 75000 },
      ]),
    ).toEqual({ budgeted: 15000, spent: 2500, percentage: 17, barPercent: 17 });
  });

  it.each([
    [10000, -12500, 125, 100],
    [0, -1000, null, 100],
    [0, 0, null, 0],
    [-1000, -500, null, 100],
  ])("handles budget %s and activity %s without invalid bar widths", (budgeted, spent, percentage, barPercent) => {
    expect(categoryTotals([{ budgeted, spent }])).toEqual({
      budgeted,
      spent: Math.max(0, -spent),
      percentage,
      barPercent,
    });
  });

  it("returns zero totals when there are no categories", () => {
    expect(categoryTotals([])).toEqual({ budgeted: 0, spent: 0, percentage: null, barPercent: 0 });
  });

  it.each([
    { spent: -100 },
    { budgeted: 1000 },
    { budgeted: NaN, spent: -100 },
    { budgeted: 1000, spent: Infinity },
  ])("does not present incomplete data as a complete total (%j)", (category) => {
    expect(categoryTotals([{ budgeted: 1000, spent: -500 }, category])).toBeNull();
  });
});
