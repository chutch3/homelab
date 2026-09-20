export function fmt(cents) {
  const abs = Math.abs(cents);
  const s = (abs / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${cents < 0 ? "-" : ""}$${s}`;
}

// Used by the floor check. Card credits do not
// offset debt on another card; the bar is bounded but headroom is not.
export function cardCoverage(checking, cards) {
  const owed = -cards.reduce((sum, card) => sum + Math.min(card.balance, 0), 0);
  return {
    owed: owed === 0 ? 0 : owed,
    headroom: checking - owed,
    percent: owed > 0 ? Math.round(Math.max(0, Math.min(100, (checking / owed) * 100))) : null,
  };
}

// Shared by drift detection and its presentation. Zero reports any growth;
// the daily runner supplies the household's configured threshold to both.
export function cardGrowth(cards, snapshotCards, thresholdCents = 0) {
  const grown = [];
  for (const card of cards) {
    const then = snapshotCards[card.name];
    if (then === undefined) continue;
    const growth = then - card.balance;
    if (growth > thresholdCents) {
      grown.push({ name: card.name, growth, now: card.balance, then });
    }
  }
  return grown;
}

// Actual stores spending as negative net activity. Keep the uncapped percentage
// for reporting while bounding the fraction used by a progress bar.
export function categoryActivity({ balance, spent }) {
  if (!Number.isFinite(spent)) return null;
  const available = balance - spent;
  const used = Math.max(0, -spent);
  const percentage = available > 0 ? Math.round((used / available) * 100) : null;
  return {
    available,
    spent: used,
    inflow: Math.max(0, spent),
    percentage,
    barPercent: percentage === null ? (used > 0 ? 100 : 0) : Math.min(100, percentage),
  };
}

// Monthly configured budgets exclude carryover. Match each category's net
// spending, so an inflow in another category cannot hide that spending.
export function categoryTotals(categories) {
  if (categories.some(({ budgeted, spent }) => !Number.isFinite(budgeted) || !Number.isFinite(spent))) {
    return null;
  }
  const budgeted = categories.reduce((sum, category) => sum + category.budgeted, 0);
  const spent = categories.reduce((sum, category) => sum + Math.max(0, -category.spent), 0);
  const percentage = budgeted > 0 ? Math.round((spent / budgeted) * 100) : null;
  return {
    budgeted,
    spent,
    percentage,
    barPercent: percentage === null ? (spent > 0 ? 100 : 0) : Math.min(100, percentage),
  };
}
