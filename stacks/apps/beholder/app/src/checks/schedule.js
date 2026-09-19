// Compare posted outflows with exact amounts in the configured account schedules.
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
  const comparisons = wrong.map(({ w, t }) => ({
    label: w.label,
    date: t.date,
    expected: Math.abs(w.expectedAmount),
    recorded: Math.abs(t.amount),
    difference: Math.abs(t.amount) - Math.abs(w.expectedAmount),
  }));
  return {
    check: "schedule",
    comparisons,
    postings: wrong.map(({ t }) => t),
  };
}
