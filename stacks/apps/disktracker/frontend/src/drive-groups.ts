import type { Drive, OfferSummary } from './api';

export type DriveGroup = { key: string; drive: Drive; listings: OfferSummary[]; representative: OfferSummary };

export const groupKeyFor = (listing: OfferSummary): string => `drive:${listing.drive.id}`;

export type KnownDrive = { mpn: string; title: string };

/** Each drive already recorded, by MPN, named by the title of the first listing seen for it. */
export function knownDrives(listings: OfferSummary[]): KnownDrive[] {
  const titles = new Map<string, string>();
  for (const listing of listings) {
    if (!titles.has(listing.drive.mpn)) titles.set(listing.drive.mpn, listing.title);
  }
  return [...titles].sort(([a], [b]) => a.localeCompare(b)).map(([mpn, title]) => ({ mpn, title }));
}
