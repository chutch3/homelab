import { describe, expect, it } from "vitest";
import { cardCoverage, cardGrowth, fmt } from "../../src/money.js";

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
