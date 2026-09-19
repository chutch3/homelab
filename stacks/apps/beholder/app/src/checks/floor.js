import { cardCoverage, fmt } from "../money.js";

// The floor rule: checking must cover what the cards currently owe.
// Card balances are negative when money is owed.
export function floorCheck({ checkingBalance, cards }) {
  const { owed, headroom } = cardCoverage(checkingBalance, cards);
  if (headroom >= 0) return null;
  return {
    check: "floor",
    summary: `Checking is ${fmt(-headroom)} below the card floor (holds ${fmt(checkingBalance)}, cards owe ${fmt(owed)}).`,
    detail: cards
      .filter((c) => c.balance < 0)
      .map((c) => `  ${c.name}: ${fmt(c.balance)}`)
      .join("\n"),
  };
}
