import { expect, it } from "vitest";
import { date, month, sortByName } from "../../../src/email/helpers.js";

it("formats date-only values in UTC including month boundaries", () => {
  expect(date("2026-01-01")).toBe("January 1, 2026");
  expect(month("2026-01-01")).toBe("January");
});

it("sorts names for presentation without mutating or escaping report data", () => {
  const rows = [{ name: "Zero" }, { name: "<Food> & drink" }];
  expect(sortByName(rows)).toEqual([rows[1], rows[0]]);
  expect(rows.map((row) => row.name)).toEqual(["Zero", "<Food> & drink"]);
});
