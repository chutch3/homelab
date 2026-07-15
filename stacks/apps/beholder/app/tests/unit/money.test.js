import { describe, expect, it } from "vitest";
import { fmt } from "../../src/money.js";

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
