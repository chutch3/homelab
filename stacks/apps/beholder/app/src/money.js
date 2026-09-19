export function fmt(cents) {
  const abs = Math.abs(cents);
  const s = (abs / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${cents < 0 ? "-" : ""}$${s}`;
}

// Shared by the floor check and daily cash summary. Card credits do not
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
