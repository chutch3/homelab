import { emptySpecifications } from '../../src/specifications';
import described from './source-kinds.json';
import type { Inventory, StoreFreshness, SourceInput, DecisionResult, MergeResult, FoundDrives, PriceRanges, Market, PriceMark, PricePage, PriceResult, Run, CollectorStatus, ConditionRule, Drive, ListingFacts, Page, Source, SourceInspection, SourceKindDescription, SourcePreview, Offer, OfferSummary, Observation, Trends, ReviewItem } from '../../src/api';

export const checkedAt = new Date('2026-09-22T12:00:00Z');
export function makeDrive(mpn: string, fields: Partial<Drive> = {}): Drive {
  return { id: `drive-${mpn}`, mpn, aliases: [], brand: null, capacity_gb: 18000, specifications: emptySpecifications(), ...fields };
}
/** A source: a store offers are recorded under, collected (Shopify here) unless entered by hand.
 * Fields of another kind come with that kind's settings. */
export function makeSource(key: string, name: string, fields: Partial<Source> = {}): Source {
  return {
    id: key, key, name, kind: 'shopify', base_url: `https://${key}.test`, settings: { collections: ['hard-drives'], free_shipping: false },
    schedule: '0 */8 * * *', enabled: true, transport: 'direct', basis: 'unconfirmed', obey_robots: true, notes: '', next_run_at: null, ...fields,
  } as Source;
}
/** A sitemap store's settings as the API gives them back with nothing set: every one, blank. */
export const sitemapSettings = {
  sitemap_path: '', product_path_pattern: '', free_shipping_marker: '', data_pattern: '', data_items: '', data_model_field: '',
  data_name_field: '', data_price_field: '', data_brand_field: '', data_stock_field: '', data_in_stock_value: '',
};
/** A source as the API answers once it is saved or changed: what was sent, over what it was (or
 * a new source's defaults). The backend also fills in the settings left out, which this does not:
 * the kind and its settings are as the test sent them. */
export function savedSource(input: SourceInput, was: Pick<Source, 'id' | 'key'> & Partial<Source>): Source {
  return { ...makeSource(was.key, input.name), ...was, ...input } as Source;
}
/** The stores the backend seeds, as sources: Other is entered by hand. */
export const knownStores: Source[] = [
  makeSource('serverpartdeals', 'ServerPartDeals'), makeSource('goharddrive', 'GoHardDrive'),
  makeSource('westerndigital', 'Western Digital'), makeSource('other', 'Other', { kind: 'manual', base_url: '', settings: {} }),
];
const storeName = (key: string) => knownStores.find(store => store.key === key)?.name ?? key;

export function makeOffer(id: string, fields: Partial<Offer> = {}, observation: Partial<Observation> = {}): Offer {
  const latest: Observation = {
    id: `${id}-observation`, item_price_cents: 18000, shipping_cents: 0, shipping_known: true, in_stock: true,
    observed_at: checkedAt.toISOString(), entered_at: checkedAt.toISOString(),
    notes: '', provenance: 'manual', total_cents: 18000, price_per_tb: '10.00', ...observation,
  };
  // Every offer is of a drive: by default one of its own, named for it.
  const mpn = fields.mpn ?? fields.drive?.mpn ?? `MPN-${id}`;
  return {
    id, drive: makeDrive(mpn), title: id, mpn, capacity_gb: 18000, condition: 'new', store: 'other', seller: 'Example seller',
    url: null, last_checked_at: latest.observed_at, latest, observations: [latest], doubt: null, ...fields,
    store_name: fields.store_name ?? storeName(fields.store ?? 'other'),
  };
}
export const shoppingListings = [
  makeOffer('Small drive', { capacity_gb: 12000 }, { item_price_cents: 15000, total_cents: 15000, price_per_tb: '12.50' }),
  makeOffer('Large drive', {}, { item_price_cents: 19800, total_cents: 19800, price_per_tb: '11.00' }),
  makeOffer('Pricey drive', { capacity_gb: 20000 }, { item_price_cents: 25000, shipping_cents: 1000, total_cents: 26000, price_per_tb: '13.00' }),
];

/** The kinds of store as GET /api/source-kinds gives them: those the collector reads, and stores
 * entered by hand. */
export const knownKinds = described as SourceKindDescription[];

/** A drive lookup that looks, and finds none. */
export const findsNone = async (): Promise<FoundDrives> => ({ items: [], total: 0, limit: 1, offset: 0 });

export const unusedWrites = {
  trends: async (): Promise<Trends> => { throw new Error('Not used'); },
  editOffer: async (): Promise<Offer> => { throw new Error('Not used'); },
  deletePrice: async (): Promise<null> => { throw new Error('Not used'); },
  recordPrice: async (): Promise<PriceResult> => { throw new Error('Not used'); },
  createDrive: async (): Promise<Drive> => { throw new Error('Not used'); },
  editDrive: async (): Promise<Drive> => { throw new Error('Not used'); },
  addAlias: async (): Promise<Drive> => { throw new Error('Not used'); },
  mergeDrive: async (): Promise<MergeResult> => { throw new Error('Not used'); },
  reviewItems: async (): Promise<Page<ReviewItem>> => ({ items: [], total: 0 }),
  decide: async (): Promise<DecisionResult> => { throw new Error('Not used'); },
  deleteOffer: async (): Promise<void> => { throw new Error('Not used'); },
  market: async (): Promise<Market> => { throw new Error('Not used'); },
  driveInventory: async (): Promise<Inventory> => { throw new Error('Not used'); },
  storeFreshness: async (): Promise<StoreFreshness[]> => { throw new Error('Not used'); },
  drive: async (): Promise<Drive> => { throw new Error('Not used'); },
  driveOffers: async (): Promise<OfferSummary[]> => { throw new Error('Not used'); },
  priceRanges: async (): Promise<PriceRanges> => ({}),
  findDrives: async (): Promise<FoundDrives> => { throw new Error('Not used'); },
  offer: async (): Promise<Offer> => { throw new Error('Not used'); },
  prices: async (): Promise<PricePage> => { throw new Error('Not used'); },
  offersToRecheck: async (): Promise<OfferSummary[]> => [],
  pricesToday: async (): Promise<PriceMark[]> => [],
  latestRuns: async (): Promise<Run[]> => { throw new Error('Not used'); },
  recentRuns: async (): Promise<Run[]> => { throw new Error('Not used'); },
  readListing: async (): Promise<ListingFacts> => { throw new Error('Not used'); },
  listSources: async (): Promise<Source[]> => { throw new Error('Not used'); },
  listSourceKinds: async (): Promise<SourceKindDescription[]> => { throw new Error('Not used'); },
  addSource: async (): Promise<Source> => { throw new Error('Not used'); },
  updateSource: async (): Promise<Source> => { throw new Error('Not used'); },
  runSource: async (): Promise<Source> => { throw new Error('Not used'); },
  stopSource: async (): Promise<Source> => { throw new Error('Not used'); },
  collectorStatus: async (): Promise<CollectorStatus> => { throw new Error('Not used'); },
  deleteSource: async (): Promise<void> => { throw new Error('Not used'); },
  previewSource: async (): Promise<SourcePreview> => { throw new Error('Not used'); },
  inspectLink: async (): Promise<SourceInspection> => { throw new Error('Not used'); },
  listConditionRules: async (): Promise<ConditionRule[]> => { throw new Error('Not used'); },
  replaceConditionRules: async (): Promise<ConditionRule[]> => { throw new Error('Not used'); },
};

export const historyPrices: Observation[] = [
  { ...makeOffer('history').latest, id: 'previous', observed_at: '2026-09-14T12:00:00Z',
    entered_at: '2026-09-14T12:00:00Z', item_price_cents: 22000, shipping_cents: 1000,
    total_cents: 23000, price_per_tb: '12.78' },
  { ...makeOffer('history').latest, id: 'current', observed_at: '2026-09-18T12:00:00Z',
    entered_at: '2026-09-18T12:00:00Z', item_price_cents: 19500, shipping_cents: 2000,
    total_cents: 21500, price_per_tb: '11.94' },
];

export function makeReviewItem(id: string, fields: Partial<ReviewItem> = {}): ReviewItem {
  return {
    id, store: 'serverpartdeals', url: `https://www.serverpartdeals.com/products/${id}`, title: id,
    seller: '', mpn: null, condition: null, capacity_gb: null, aliases: [], brand: null, specifications: null, conflict_mpn: null, conflict_drive_id: null,
    item_price_cents: 36999, shipping_cents: 0, in_stock: true, reason: 'missing_mpn',
    provenance: 'collected', first_seen_at: checkedAt.toISOString(), last_seen_at: checkedAt.toISOString(), drive: null, ...fields,
  };
}

/** What the API answers once a price is recorded for an offer: priceId is the price made, or null
 * when it was the same as the offer's last and so only counted as a check. */
export const recordedOn = (offer: { id: string }, priceId: string | null = null): PriceResult =>
  ({ status: 'recorded', offer_id: offer.id, price_id: priceId, review_item_id: null });
