import { emptySpecifications } from '../../src/specifications';
import described from '../../../backend/disktracker/source_kinds.json';
import type { CollectorRun, CollectorStatus, ConditionRule, Drive, ListingFacts, Page, Source, SourceInspection, SourceKindDescription, SourcePreview, Listing, ListingSummary, Observation, UnmatchedItem } from '../../src/api';

export const checkedAt = new Date('2026-09-22T12:00:00Z');
export function makeDrive(mpn: string, fields: Partial<Drive> = {}): Drive {
  return { id: `drive-${mpn}`, mpn, aliases: [], brand: null, capacity_gb: 18000, specifications: emptySpecifications(), ...fields };
}
/** A source: a store offers are recorded under, collected (Shopify here) unless entered by hand. */
export function makeSource(key: string, name: string, fields: Partial<Source> = {}): Source {
  return {
    id: key, key, name, kind: 'shopify', base_url: `https://${key}.test`, settings: { collections: ['hard-drives'] },
    schedule: '0 */8 * * *', enabled: true, transport: 'direct', basis: 'unconfirmed', notes: '', next_run_at: null, ...fields,
  };
}
/** The stores the backend seeds, as sources: Other is entered by hand. */
export const knownStores: Source[] = [
  makeSource('serverpartdeals', 'ServerPartDeals'), makeSource('goharddrive', 'GoHardDrive'),
  makeSource('westerndigital', 'Western Digital'), makeSource('other', 'Other', { kind: 'manual', base_url: '', settings: {} }),
];
const storeName = (key: string) => knownStores.find(store => store.key === key)?.name ?? key;

export function makeListing(id: string, fields: Partial<Listing> = {}, observation: Partial<Observation> = {}): Listing {
  const latest: Observation = {
    id: `${id}-observation`, item_price_cents: 18000, shipping_cents: 0, shipping_known: true, in_stock: true,
    observed_at: checkedAt.toISOString(), entered_at: checkedAt.toISOString(),
    notes: '', acquisition_method: 'manual', total_cents: 18000, price_per_tb: '10.00', ...observation,
  };
  return {
    id, drive: null, title: id, mpn: null, capacity_gb: 18000, condition: 'new', store: 'other', seller: 'Example seller',
    url: null, last_checked_at: latest.observed_at, latest, observations: [latest], ...fields,
    store_name: fields.store_name ?? storeName(fields.store ?? 'other'),
  };
}
export const shoppingListings = [
  makeListing('Small drive', { capacity_gb: 12000 }, { item_price_cents: 15000, total_cents: 15000, price_per_tb: '12.50' }),
  makeListing('Large drive', {}, { item_price_cents: 19800, total_cents: 19800, price_per_tb: '11.00' }),
  makeListing('Pricey drive', { capacity_gb: 20000 }, { item_price_cents: 25000, shipping_cents: 1000, total_cents: 26000, price_per_tb: '13.00' }),
];

/** The kinds of store as the backend gives them: those the collector's readers describe (the very
 * file the backend serves them from), and stores entered by hand. */
export const knownKinds: SourceKindDescription[] = [
  ...Object.entries(described).map(([kind, kindOf]) => ({ kind, collected: true, ...kindOf }) as SourceKindDescription),
  { kind: 'manual', label: 'Entered by hand', collected: false, page_test: false, groups: [], settings: [] },
];

export const unusedWrites = {
  editOffer: async (): Promise<Listing> => { throw new Error('Not used'); },
  deletePrice: async (): Promise<Listing | null> => { throw new Error('Not used'); },
  recordPrice: async (): Promise<Listing> => { throw new Error('Not used'); },
  replaceSpecifications: async (): Promise<Drive> => { throw new Error('Not used'); },
  addAlias: async (): Promise<Drive> => { throw new Error('Not used'); },
  listUnmatched: async (): Promise<Page<UnmatchedItem>> => ({ items: [], total: 0 }),
  resolveUnmatched: async (): Promise<Listing> => { throw new Error('Not used'); },
  ignoreUnmatched: async (): Promise<void> => { throw new Error('Not used'); },
  deleteOffer: async (): Promise<void> => { throw new Error('Not used'); },
  list: async (): Promise<ListingSummary[]> => { throw new Error('Not used'); },
  priceHistory: async (): Promise<Listing[]> => { throw new Error('Not used'); },
  latestRuns: async (): Promise<CollectorRun[]> => { throw new Error('Not used'); },
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
  { ...makeListing('history').latest, id: 'previous', observed_at: '2026-09-14T12:00:00Z',
    entered_at: '2026-09-14T12:00:00Z', item_price_cents: 22000, shipping_cents: 1000,
    total_cents: 23000, price_per_tb: '12.78' },
  { ...makeListing('history').latest, id: 'current', observed_at: '2026-09-18T12:00:00Z',
    entered_at: '2026-09-18T12:00:00Z', item_price_cents: 19500, shipping_cents: 2000,
    total_cents: 21500, price_per_tb: '11.94' },
];

export function makeUnmatched(id: string, fields: Partial<UnmatchedItem> = {}): UnmatchedItem {
  return {
    id, source: 'serverpartdeals', url: `https://www.serverpartdeals.com/products/${id}`, title: id,
    seller: '', mpn: null, condition: null, capacity_gb: null,
    item_price_cents: 36999, shipping_cents: 0, in_stock: true, reason: 'missing_mpn',
    first_seen_at: checkedAt.toISOString(), last_seen_at: checkedAt.toISOString(), ...fields,
  };
}
