import type { Drive, ListingSummary } from './api';
import { compareListings, type Sort } from './listing-query';

export type DriveGroup = { key: string; drive: Drive | null; listings: ListingSummary[]; representative: ListingSummary };

export const groupKeyFor = (listing: ListingSummary): string =>
  listing.drive ? `drive:${listing.drive.id}` : `listing:${listing.id}`;

export function groupByDrive(listings: ListingSummary[], sort: Sort): DriveGroup[] {
  const byKey = new Map<string, { drive: Drive | null; listings: ListingSummary[] }>();
  for (const listing of listings) {
    const key = groupKeyFor(listing);
    const group = byKey.get(key) ?? { drive: listing.drive, listings: [] };
    group.listings.push(listing);
    byKey.set(key, group);
  }
  const compare = compareListings(sort), cheapest = compareListings('unit-asc');
  // A drive is shown by its cheapest offer in stock, whichever way the list is ordered.
  const groups = [...byKey.entries()].map(([key, group]) => ({
    key, drive: group.drive, listings: group.listings,
    representative: [...group.listings].sort((a, b) => Number(b.latest.in_stock) - Number(a.latest.in_stock) || cheapest(a, b))[0],
  }));
  return groups.sort((a, b) => compare(a.representative, b.representative));
}

export type KnownDrive = { mpn: string; title: string };

/** Each drive already recorded, by MPN, named by the title of the first listing seen for it. */
export function knownDrives(listings: ListingSummary[]): KnownDrive[] {
  const titles = new Map<string, string>();
  for (const listing of listings) {
    if (listing.drive && !titles.has(listing.drive.mpn)) titles.set(listing.drive.mpn, listing.title);
  }
  return [...titles].sort(([a], [b]) => a.localeCompare(b)).map(([mpn, title]) => ({ mpn, title }));
}
