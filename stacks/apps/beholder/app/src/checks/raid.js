import { fmt } from "../money.js";

// Any inflow categorized to the savings category means money came back out
// of savings. Deliberate irregulars get recategorized to their event
// category, so anything still here is either unprocessed or a raid.
export function raidCheck({ savingsInflows }) {
  if (!savingsInflows || savingsInflows.length === 0) return null;
  const total = savingsInflows.reduce((s, t) => s + t.amount, 0);
  return {
    check: "raid",
    summary: `${fmt(total)} came out of savings (${savingsInflows.length} transaction${savingsInflows.length > 1 ? "s" : ""}) — match to a named irregular or talk about it.`,
    detail: savingsInflows.map((t) => `  ${t.date}  ${fmt(t.amount)}  ${t.payee}`).join("\n"),
  };
}
