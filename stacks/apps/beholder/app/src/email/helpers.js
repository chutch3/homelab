export { fmt as money } from "../money.js";

export const abs = Math.abs;
export const negative = (value) => value < 0;
export const positive = (value) => value > 0;
export const eq = (left, right) => left === right;
export const isNull = (value) => value === null;
export const subtract = (left, right) => left - right;

export function date(value) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-US", {
    timeZone: "UTC",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export function month(value) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", month: "long" });
}

export function sortByName(rows) {
  return [...rows].sort((left, right) => left.name.localeCompare(right.name, "en"));
}
