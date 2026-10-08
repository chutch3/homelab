import type { ListingSummary, Store } from './api';
import type { DriveGroup } from './drive-groups';
import { isRecent } from './listing-query';

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

export const issues = ['unknown_specifications', 'stale'] as const;
export type Issue = typeof issues[number];

export function issueLabel(issue: Issue, recentDays: number): string {
  return issue === 'stale' ? `Not checked in ${recentDays} days` : 'Unknown specifications';
}

/** What is missing or out of date for a drive: nothing known of its specifications, or an
 * in-stock offer not checked within the recent window. */
export function driveIssues(group: DriveGroup, now: Date, recentDays: number): Issue[] {
  const specifications = group.drive?.specifications;
  const unknown = !specifications || (
    [specifications.media_type, specifications.form_factor, specifications.interface, specifications.recording_type]
      .every(value => value === 'unknown') && specifications.intended_use.length === 0);
  const found: Issue[] = [];
  if (unknown) found.push('unknown_specifications');
  if (group.listings.some(listing => listing.latest.in_stock && !isRecent(listing, now, recentDays))) found.push('stale');
  return found;
}

export type Freshness = { store: Store; offers: number; latest: string; medianAgeMs: number };

/** How recently each store's offers were checked, in the order stores are listed. */
export function freshness(listings: ListingSummary[], now: Date, stores: Store[]): Freshness[] {
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

export function ageLabel(ms: number): string {
  if (ms < HOUR) return 'under an hour';
  if (ms < 2 * DAY) {
    const count = Math.floor(ms / HOUR);
    return `${count} hour${count === 1 ? '' : 's'}`;
  }
  return `${Math.floor(ms / DAY)} days`;
}

/** How long something has gone on, or how long ago it was: to the minute within the hour, where
 * a collector's last word or a run's length is worth that much. */
export function elapsedLabel(ms: number): string {
  if (ms < 60_000) return 'under a minute';
  if (ms >= HOUR) return ageLabel(ms);
  const minutes = Math.floor(ms / 60_000);
  return `${minutes} minute${minutes === 1 ? '' : 's'}`;
}

/** Hand-entered offers last checked before the recent window, oldest first: collectors keep
 * their own offers current, so only these wait on a person. */
export function overdueForRecheck(listings: ListingSummary[], now: Date, recentDays: number): ListingSummary[] {
  return listings
    .filter(listing => listing.latest.acquisition_method === 'manual' && !isRecent(listing, now, recentDays))
    .sort((a, b) => a.last_checked_at.localeCompare(b.last_checked_at));
}
