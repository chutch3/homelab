function merchantName(value) {
  return (value ?? "")
    .toLowerCase()
    .replace(/[’']/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function sameMerchant(a, b) {
  const first = merchantName(a);
  const second = merchantName(b);
  if (first.length < 4 || second.length < 4) return false;
  if (first === second) return true;
  const [shorter, longer] = [first, second].sort((a, b) => a.length - b.length);
  return shorter.split(" ").length >= 2 && longer.startsWith(`${shorter} `);
}

// Review candidates only: never merge or delete transactions. Require a unique
// pending/posted pairing so repeated visits cannot silently choose a winner.
export function duplicatesCheck({ transactions, windowDays, maxIncreasePercent, holdMaxCents }) {
  const importedSpending = transactions.filter(
    (t) => t.importedId && Number.isFinite(t.amount) && t.amount < 0,
  );
  const pending = importedSpending.filter((t) => t.cleared === false);
  const posted = importedSpending.filter((t) => t.cleared === true);
  const candidates = [];
  for (const first of pending) {
    for (const final of posted) {
      if (first.accountId !== final.accountId || first.importedId === final.importedId) continue;
      const days = Math.abs(Date.parse(first.date) - Date.parse(final.date)) / 86400000;
      if (!Number.isFinite(days) || days > windowDays || !sameMerchant(first.merchant, final.merchant))
        continue;
      const original = -first.amount;
      const settled = -final.amount;
      const isSmallHold = original <= holdMaxCents;
      const withinIncreaseLimit = settled * 100 <= original * (100 + maxIncreasePercent);
      if (settled <= original || (!isSmallHold && !withinIncreaseLimit)) continue;
      candidates.push({ pending: first, posted: final });
    }
  }
  const pairs = candidates
    .filter(
      (pair) =>
        candidates.filter((other) => other.pending.id === pair.pending.id).length === 1 &&
        candidates.filter((other) => other.posted.id === pair.posted.id).length === 1,
    )
    .sort(
      (a, b) =>
        b.pending.date.localeCompare(a.pending.date) || a.pending.merchant.localeCompare(b.pending.merchant),
    );
  return pairs.length ? { check: "duplicates", pairs } : null;
}
