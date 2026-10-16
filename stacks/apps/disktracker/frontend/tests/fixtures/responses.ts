import type { DriveDetail, DrivePage, DriveQuery, DriveRow, FilterOptions, Offer, OfferSummary, PricePage, PriceRequest } from '../../src/api';
import { groupKeyFor } from '../../src/drive-groups';
import { checkedAt } from './listings';

/** Responses as the server gives them, written out by each test: nothing here filters, orders,
 * groups by price or works anything out. The server's own tests say what it works out. */

const summary = ({ observations: _history, ...rest }: Offer | OfferSummary & { observations?: unknown }) => rest as OfferSummary;
export const noOptions = (): FilterOptions => ({ brands: [], capacities: [], conditions: [] });

/** One row for each drive among these offers, in the order its first offer comes; the row is shown
 * by that first offer, and carries every offer of the drive given. */
export function rowsOf(offers: OfferSummary[], ranges: Record<string, DriveRow['range']> = {}): DriveRow[] {
  const rows = new Map<string, DriveRow>();
  for (const offer of offers) {
    const key = groupKeyFor(offer);
    const row = rows.get(key);
    if (row) row.offers.push(summary(offer));
    else rows.set(key, { key, drive: offer.drive!, representative: summary(offer), offers: [summary(offer)], range: ranges[key] ?? null });
  }
  return [...rows.values()];
}

/** A page of these rows, as asked for: total, offers and options as given, or as the rows say. */
export function drivePage(rows: DriveRow[], fields: Partial<DrivePage> = {}, query?: Pick<DriveQuery, 'limit' | 'offset'>): DrivePage {
  const limit = query?.limit ?? 50, offset = query?.offset ?? 0;
  return {
    items: rows.slice(offset, offset + limit), total: rows.length, offers: rows.reduce((sum, row) => sum + row.offers.length, 0),
    sold_out: 0, limit, offset, as_of: checkedAt.toISOString(), lowest: { total: [], unit: [] }, filter_options: noOptions(), ...fields,
  };
}

/** A drive as the server reads it: these offers of it, with the ranges given. */
export function detailOf(offers: Offer[], ranges: DriveDetail['ranges'] = {}): DriveDetail {
  return { drive: offers[0].drive!, offers: offers.map(summary), ranges };
}

/** These offers' prices, a part at a time. */
export function pricesOf(offers: Offer[], { limit = 500, offset = 0 }: PriceRequest): PricePage {
  const all = offers.flatMap(offer => offer.observations.map(price => ({ ...price, offer_id: offer.id })));
  return { items: all.slice(offset, offset + limit), total: all.length, limit, offset };
}
