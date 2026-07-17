import { fmt } from "../money.js";

// Uncategorized spending corrupts every downstream number (budget vs
// actual, category netting, the monthly report). Transfers never appear
// here — card payments are legitimately uncategorized.
export function uncategorizedCheck({ uncategorized }) {
  if (!uncategorized || uncategorized.length === 0) return null;
  return {
    check: "uncategorized",
    summary: `${uncategorized.length} transaction${uncategorized.length > 1 ? "s" : ""} on budget accounts ha${uncategorized.length > 1 ? "ve" : "s"} no category — categorize them so the budget stays true.`,
    detail: uncategorized.map((t) => `  ${t.date}  ${fmt(t.amount)}  ${t.payee}  (${t.account})`).join("\n"),
    transactions: uncategorized,
  };
}
