import type { Drive, OfferSummary } from './api';

export type DriveGroup = { key: string; drive: Drive; listings: OfferSummary[]; representative: OfferSummary };

export const groupKeyFor = (listing: OfferSummary): string => `drive:${listing.drive.id}`;
