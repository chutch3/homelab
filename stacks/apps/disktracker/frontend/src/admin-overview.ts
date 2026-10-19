import type { OfferSummary, Run, Store } from './api';

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

export const issues = ['unknown_specifications', 'stale'] as const;
export type Issue = typeof issues[number];

/** What a drive may need (the server says which it does), in a few characters for a count or a column; Stale is an in-stock offer unchecked for longer than the recent window. */
export function issueLabel(issue: Issue): string {
  return issue === 'stale' ? 'Stale' : 'No specs';
}

export type Freshness = { store: Store; offers: number; latest: string; medianAgeMs: number };

/** How recently each store's offers were checked, in the order stores are listed. */
export function freshness(listings: OfferSummary[], now: Date, stores: Store[]): Freshness[] {
  return stores.flatMap(store => {
    const value = store.key;
    const checked = listings.filter(listing => listing.store === value).map(listing => listing.last_checked_at)
      .sort((a, b) => b.localeCompare(a));
    if (!checked.length) return [];
    const ages = checked.map(at => now.getTime() - Date.parse(at));
    const middle = Math.floor(ages.length / 2);
    const medianAgeMs = ages.length % 2 ? ages[middle] : (ages[middle - 1] + ages[middle]) / 2;
    return [{ store, offers: checked.length, latest: checked[0], medianAgeMs }];
  });
}

/** An age in a few characters, for a column of them: hours up to two days, then days. */
export function ageLabel(ms: number): string {
  if (ms < HOUR) return '<1h';
  return ms < 2 * DAY ? `${Math.floor(ms / HOUR)}h` : `${Math.floor(ms / DAY)}d`;
}

/** How long something has gone on, or how long ago it was: to the minute within the hour, where
 * a collector's last word or a run's length is worth that much. */
export function elapsedLabel(ms: number): string {
  if (ms < 60_000) return 'under a minute';
  if (ms >= HOUR) return ageLabel(ms);
  const minutes = Math.floor(ms / 60_000);
  return `${minutes} minute${minutes === 1 ? '' : 's'}`;
}

/** A run that failed, or that its collector lost: not one that completed, was stopped, or is still going. */
export const endedBadly = (run: Run) => run.status === 'failed' || run.status === 'abandoned';
