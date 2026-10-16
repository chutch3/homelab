import type { Drive, OfferSummary } from './api';
import { compareListings, type Sort } from './listing-query';

export type DriveGroup = { key: string; drive: Drive; listings: OfferSummary[]; representative: OfferSummary };

export const groupKeyFor = (listing: OfferSummary): string => `drive:${listing.drive.id}`;

export function groupByDrive(listings: OfferSummary[], sort: Sort): DriveGroup[] {
  const byKey = new Map<string, { drive: Drive; listings: OfferSummary[] }>();
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
  // A drive no store has in stock comes after every drive that can be bought.
  return groups.sort((a, b) => Number(b.representative.latest.in_stock) - Number(a.representative.latest.in_stock) || compare(a.representative, b.representative));
}

export type KnownDrive = { mpn: string; title: string };

/** Each drive already recorded, by MPN, named by the title of the first listing seen for it. */
export function knownDrives(listings: OfferSummary[]): KnownDrive[] {
  const titles = new Map<string, string>();
  for (const listing of listings) {
    if (!titles.has(listing.drive.mpn)) titles.set(listing.drive.mpn, listing.title);
  }
  return [...titles].sort(([a], [b]) => a.localeCompare(b)).map(([mpn, title]) => ({ mpn, title }));
}
