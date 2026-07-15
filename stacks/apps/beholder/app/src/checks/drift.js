import { fmt } from "../money.js";

// Compare each card's owed balance against the snapshot (≈30 days back).
// Debt growing past the threshold = the June-Discover pattern: spending
// outrunning the payoff, invisible until month end unless watched.
export function driftCheck({ cards, snapshotCards, thresholdCents }) {
  const grown = [];
  for (const card of cards) {
    const then = snapshotCards[card.name];
    if (then === undefined) continue;
    const growth = then - card.balance; // both negative; positive growth = more owed now
    if (growth > thresholdCents) {
      grown.push({ name: card.name, growth, now: card.balance, then });
    }
  }
  if (grown.length === 0) return null;
  return {
    check: "drift",
    summary: grown
      .map(
        (g) => `${g.name} debt grew ${fmt(g.growth)} over the last month (${fmt(g.then)} -> ${fmt(g.now)}).`,
      )
      .join(" "),
    detail: "Paying in full but owing more each month means spending is outrunning the budget.",
  };
}
