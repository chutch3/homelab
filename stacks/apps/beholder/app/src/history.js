// History rules are pure; state.js owns reading and writing the persisted JSON.
const SNAPSHOT_KEEP_DAYS = 60;
const DRIFT_LOOKBACK_DAYS = 30;

function daysBetween(a, b) {
  return Math.abs(new Date(a) - new Date(b)) / 86400000;
}

// Snapshot nearest to `lookback` days ago (any history counts; drift needs
// a baseline, not a precise one).
export function driftBaseline(snapshots = [], now) {
  if (snapshots.length === 0) return null;
  const target = new Date(now.getTime() - DRIFT_LOOKBACK_DAYS * 86400000);
  return snapshots.reduce(
    (best, s) =>
      !best || Math.abs(new Date(s.date) - target) < Math.abs(new Date(best.date) - target) ? s : best,
    null,
  );
}

// Event findings (raid, schedule) are deduped across runs via state so a
// wide sync-lag-tolerant lookback does not nag daily; condition findings
// (floor, drift, duplicates) deliberately repeat until resolved.
const raidKey = (t) => `raid:${t.id ?? `${t.date}:${t.amount}:${t.payee}`}`;
const scheduleKey = (t) => `schedule:${t.payeeId}:${t.date}:${t.amount}`;
const uncategorizedKey = (t) => `uncat:${t.id ?? `${t.date}:${t.amount}:${t.payee}`}`;

export function pruneNotifications(alerted, today) {
  const kept = {};
  for (const [key, date] of Object.entries(alerted ?? {})) {
    if (daysBetween(date, today) <= SNAPSHOT_KEEP_DAYS) kept[key] = date;
  }
  return kept;
}

const notificationKeys = { raid: raidKey, schedule: scheduleKey, uncategorized: uncategorizedKey };

export function unnotifiedTransactions(transactions, check, alerted) {
  const key = notificationKeys[check];
  return transactions.filter((transaction) => !alerted[key(transaction)]);
}

export function recordSnapshot(snapshots = [], { date, checking, cards }) {
  return snapshots
    .filter((snapshot) => snapshot.date !== date && daysBetween(snapshot.date, date) <= SNAPSHOT_KEEP_DAYS)
    .concat([{ date, checking, cards: Object.fromEntries(cards.map((card) => [card.name, card.balance])) }])
    .sort((left, right) => left.date.localeCompare(right.date));
}

// Called only after delivery succeeds. Condition findings deliberately repeat.
export function recordNotifications(alerted, findings, today) {
  const updated = { ...alerted };
  for (const finding of findings) {
    let transactions;
    if (finding.check === "raid" || finding.check === "uncategorized") {
      transactions = finding.transactions;
    } else if (finding.check === "schedule") {
      transactions = finding.postings;
    } else {
      continue;
    }
    const key = notificationKeys[finding.check];
    for (const transaction of transactions) updated[key(transaction)] = today;
  }
  return updated;
}
