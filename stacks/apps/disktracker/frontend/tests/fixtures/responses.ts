import type { CatalogDrive, Condition, CatalogDrivePage, CatalogDriveQuery, ConditionPrices, DriveDetail, FilterOptions, Market, MarketQuery, MarketRow, Offer, OfferSummary, PricePage, PriceRequest } from '../../src/api';
import { groupOf, type DriveGroup } from '../../src/drive-groups';
import { conditions, sellerLabel } from '../../src/listing-display';
import { checkedAt } from './listings';

/** Responses as the server gives them, written out by each test: nothing here filters, orders,
 * groups by price or works anything out. The server's own tests say what it works out. */

const summary = ({ observations: _history, ...rest }: Offer | OfferSummary & { observations?: unknown }) => rest as OfferSummary;
export const noOptions = (): FilterOptions => ({ brands: [], capacities: [], conditions: [] });

/** One row for each drive among these offers, in the order its first offer comes; the row is shown
 * by that first offer, and says, as the server does of the offers that match, how many stores and
 * sellers offer it and what each condition it is offered in costs. Ranges are keyed by drive id. */
export function rowsOf(offers: OfferSummary[], ranges: Record<string, MarketRow['range']> = {}): MarketRow[] {
  const byDrive = new Map<string, OfferSummary[]>();
  for (const offer of offers) byDrive.set(offer.drive.id, [...(byDrive.get(offer.drive.id) ?? []), summary(offer)]);
  return [...byDrive.values()].map(of => ({
    drive: of[0].drive, offer: of[0], stores: new Set(of.map(sellerLabel)).size, conditions: conditionsOf(of),
    range: ranges[of[0].drive.id] ?? null,
  }));
}

/** What each condition these offers are in costs: offers, those in stock, the lowest total of those. */
function conditionsOf(offers: OfferSummary[]): ConditionPrices[] {
  return conditions.flatMap(({ value }) => {
    const of = offers.filter(offer => offer.condition === value);
    const stocked = of.filter(offer => offer.latest.in_stock).map(offer => offer.latest.total_cents);
    return of.length ? [{ condition: value as Condition, offers: of.length, in_stock: stocked.length, lowest_total_cents: stocked.length ? Math.min(...stocked) : null }] : [];
  });
}

/** A page of these rows, as asked for: total, offers and options as given, or as the rows say. */
export function marketPage(rows: MarketRow[], fields: Partial<Market> = {}, query?: Pick<MarketQuery, 'limit' | 'offset'>): Market {
  const limit = query?.limit ?? 50, offset = query?.offset ?? 0;
  return {
    items: rows.slice(offset, offset + limit), total: rows.length,
    offers: rows.reduce((sum, row) => sum + row.conditions.reduce((count, condition) => count + condition.offers, 0), 0),
    sold_out: 0, catalogued: rows.length, limit, offset, as_of: checkedAt.toISOString(), lowest: { total: [], unit: [] },
    filter_options: noOptions(), ...fields,
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

/** A page of drives to manage, one for each of these rows, named by its row's first offer; total
 * and counts as given, or as the rows say, with nothing needed. */
export function catalogPage(rows: MarketRow[], fields: Partial<CatalogDrivePage> = {}, query?: Pick<CatalogDriveQuery, 'limit' | 'offset'>): CatalogDrivePage {
  const limit = query?.limit ?? 50, offset = query?.offset ?? 0;
  const items: CatalogDrive[] = rows.map(row => ({
    drive: row.drive, title: row.offer.title, offers: row.conditions.reduce((count, condition) => count + condition.offers, 0), issues: [],
  }));
  return {
    items: items.slice(offset, offset + limit), total: items.length, all: items.length,
    issues: { unknown_specifications: 0, stale: 0 }, limit, offset, ...fields,
  };
}

/** The drive table's groups for these rows, as the app makes them of the server's: each shown by
 * its first offer given. */
export const groupsOf = (offers: OfferSummary[]): DriveGroup[] => rowsOf(offers).map(groupOf);
