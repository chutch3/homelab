import { fmt } from "../money.js";

// Watched schedules come from the budget server (exact-amount schedules on
// the checking account). A posting by a watched payee at a different amount
// means an autopay changed underneath us — e.g. the deferred-interest
// minimum-payment trap.
export function scheduleCheck({ recentTransactions, watched }) {
  const wrong = [];
  for (const w of watched) {
    const postings = recentTransactions.filter((t) => t.payeeId === w.payeeId && t.amount < 0);
    if (postings.length === 0) continue;
    // An extra payment alongside the promised one is fine; alert only when
    // the payee posted and NOTHING matches the expected amount.
    if (postings.some((t) => t.amount === w.expectedAmount)) continue;
    for (const t of postings) wrong.push({ w, t });
  }
  if (wrong.length === 0) return null;
  return {
    check: "schedule",
    summary: wrong
      .map(
        ({ w, t }) => `${w.label}: posted ${fmt(t.amount)} on ${t.date}, expected ${fmt(w.expectedAmount)}.`,
      )
      .join(" "),
    detail: "The schedule in Actual and the biller's autopay disagree — check both.",
    postings: wrong.map(({ t }) => t),
  };
}
