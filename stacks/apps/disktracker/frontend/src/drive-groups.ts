import type { MarketRow, OfferSummary } from './api';

/** A drive as the Prices table shows it: a row of the market, under the key the app selects it by. */
export type DriveGroup = MarketRow & { key: string };

export const groupKeyFor = (listing: OfferSummary): string => `drive:${listing.drive.id}`;

export const groupOf = (row: MarketRow): DriveGroup => ({ ...row, key: `drive:${row.drive.id}` });
