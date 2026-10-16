import { emptySpecifications, matchesSpecification, specOptions, type SpecKey } from './specifications';
import type { Condition, DriveScope, OfferSummary } from './api';
import { conditions, sellerLabel } from './listing-display';

export const sorts = [
  { value: 'unit-asc', label: '$/TB: low to high' }, { value: 'unit-desc', label: '$/TB: high to low' },
  { value: 'total-asc', label: 'Total: low to high' }, { value: 'total-desc', label: 'Total: high to low' },
  { value: 'capacity-asc', label: 'Capacity: low to high' }, { value: 'capacity-desc', label: 'Capacity: high to low' },
  { value: 'checked-desc', label: 'Checked most recently' }, { value: 'checked-asc', label: 'Checked longest ago' },
] as const;
export type Sort = typeof sorts[number]['value'];
/** The days a drive's price range can look back over. */
export const periods = [30, 90, 180] as const;
export type Period = typeof periods[number];
export type ListingQuery = {
  media_type: string; form_factor: string; interface: string; intended_use: string; recording_type: string;
  search: string; brands: string[]; capacities: string[]; maxTotal: string;
  conditions: string[]; stores: string[]; recentOnly: boolean; inStockOnly: boolean; sort: Sort;
  /** Not a filter: how far back each drive's price range looks. */
  days: Period;
};
export const defaultQuery = (): ListingQuery => ({
  media_type: '', form_factor: '', interface: '', intended_use: '', recording_type: '',
  search: '', brands: [], capacities: [], maxTotal: '', conditions: [], stores: [],
  // An offer that cannot be bought is left out until it is asked for.
  recentOnly: false, inStockOnly: true, sort: 'unit-asc', days: 90,
});
const DAY = 86_400_000;

export function isRecent(listing: OfferSummary, now: Date, days: number): boolean {
  const age = now.getTime() - Date.parse(listing.last_checked_at);
  return age >= 0 && age <= days * DAY;
}

export function queryErrors(query: ListingQuery): Record<string, string> {
  const errors: Record<string, string> = {};
  // Totals are in dollars and cents.
  const total = query.maxTotal.trim();
  if (total && (!/^\d+(\.\d{1,2})?$/.test(total) || !Number.isSafeInteger(Math.round(Number(total) * 100)))) {
    errors.maxTotal = 'Enter a non-negative number with up to two decimal places.';
  }
  return errors;
}

export function queryListings(listings: OfferSummary[], query: ListingQuery, now: Date, recentDays: number): OfferSummary[] {
  if (Object.keys(queryErrors(query)).length) return [];
  const search = query.search.trim().toLowerCase();
  const rows = listings.filter(listing => {
    const capacity = listing.capacity_gb, total = listing.latest.total_cents;
    // Search covers every name a drive or offer goes by: title, MPN, other MPNs, and seller.
    const names = `${listing.title} ${listing.mpn ?? ''} ${(listing.drive?.aliases ?? []).join(' ')} ${sellerLabel(listing)}`;
    return (!search || names.toLowerCase().includes(search))
      && (!query.brands.length || query.brands.includes(listing.drive?.brand ?? UNKNOWN_BRAND))
      && (!query.capacities.length || query.capacities.includes(String(capacity)))
      && (!query.maxTotal.trim() || (total !== null && total <= Math.round(Number(query.maxTotal) * 100)))
      && (!query.conditions.length || query.conditions.includes(listing.condition))
      && (!query.stores.length || query.stores.includes(listing.store))
      && (!query.inStockOnly || listing.latest.in_stock)
      && (Object.keys(specOptions) as SpecKey[]).every(key => matchesSpecification(listing.drive?.specifications ?? emptySpecifications(), key, query[key]))
      && (!query.recentOnly || isRecent(listing, now, recentDays));
  });
  return rows.sort(compareListings(query.sort));
}

/** The brand filter's value for drives no source has named a brand for. */
export const UNKNOWN_BRAND = 'unknown';
export const brandLabel = (brand: string) => brand === UNKNOWN_BRAND ? 'Unknown' : brand;
export type BrandCount = { brand: string; drives: number };

export type ConditionCount = { condition: Condition; drives: number };

export type CapacityCount = { capacity_gb: number; drives: number };

export function sortValue(sort: Sort, listing: OfferSummary): number | null {
  const column = sort.split('-')[0];
  if (column === 'capacity') return listing.capacity_gb;
  if (column === 'checked') return Date.parse(listing.last_checked_at);
  if (column === 'total') return listing.latest.total_cents;
  return listing.latest.price_per_tb === null ? null : Number(listing.latest.price_per_tb);
}

export function compareListings(sort: Sort): (a: OfferSummary, b: OfferSummary) => number {
  const direction = sort.split('-')[1];
  return (a, b) => {
    const left = sortValue(sort, a), right = sortValue(sort, b);
    if (left === null && right !== null) return 1;
    if (right === null && left !== null) return -1;
    const difference = left === null || right === null ? 0 : (left - right) * (direction === 'asc' ? 1 : -1);
    return difference || a.id.localeCompare(b.id);
  };
}

const specParams = { media_type: 'media', form_factor: 'form', interface: 'interface', intended_use: 'use', recording_type: 'recording' };
const textParams = { search: 'q', maxTotal: 'maxTotal' } as const;
export function readQuery(search: string): ListingQuery {
  const params = new URLSearchParams(search), query = defaultQuery();
  for (const [field, parameter] of Object.entries(textParams)) {
    query[field as keyof typeof textParams] = params.get(parameter) ?? '';
  }
  for (const key of Object.keys(specParams) as SpecKey[]) {
    const value = params.get(specParams[key]);
    if (value === 'unknown' || specOptions[key].some(option => option.value === value)) query[key] = value!;
  }
  query.brands = [...new Set(params.getAll('brand').filter(Boolean))];
  query.capacities = [...new Set(params.getAll('capacity').filter(value => /^[1-9]\d*$/.test(value)))];
  query.conditions = [...new Set(params.getAll('condition').filter(value => conditions.some(condition => condition.value === value)))];
  query.stores = [...new Set(params.getAll('store').filter(Boolean))];
  query.recentOnly = params.get('recent') === '1';
  query.inStockOnly = params.get('stock') !== 'all';
  const sort = params.get('sort');
  if (sorts.some(option => option.value === sort)) query.sort = sort as Sort;
  const days = periods.find(period => String(period) === params.get('days'));
  if (days) query.days = days;
  return query;
}
/** Which drives the filters narrow to, as the API takes it: what a report of them is of. */
export function scopeOf(query: ListingQuery): DriveScope {
  const spec = (value: string) => value || undefined;
  return {
    ...(query.search.trim() ? { q: query.search.trim() } : {}),
    ...(query.brands.length ? { brand: query.brands } : {}),
    ...(query.capacities.length ? { capacity: query.capacities.map(Number) } : {}),
    ...(query.conditions.length ? { condition: query.conditions as Condition[] } : {}),
    ...(query.stores.length ? { store: query.stores } : {}),
    ...Object.fromEntries((['media_type', 'form_factor', 'interface', 'recording_type', 'intended_use'] as const)
      .flatMap(key => spec(query[key]) ? [[key, query[key]]] : [])),
  };
}

/** The filters that narrow which drives, as a URL's query, and nothing of order, stock or period. */
export function scopeSearch(query: ListingQuery): string {
  const { search, brands, capacities, conditions, stores, media_type, form_factor, interface: connection, intended_use, recording_type } = query;
  return writeQuery({ ...defaultQuery(), search, brands, capacities, conditions, stores, media_type, form_factor, interface: connection, intended_use, recording_type });
}

export function writeQuery(query: ListingQuery, current = ''): string {
  const params = new URLSearchParams(current);
  for (const [field, parameter] of Object.entries(textParams)) {
    params.delete(parameter);
    const value = query[field as keyof typeof textParams];
    if (value) params.set(parameter, value);
  }
  for (const parameter of ['brand', 'capacity', 'condition', 'store', 'recent', 'stock', 'sort', 'days']) params.delete(parameter);
  for (const key of Object.keys(specParams) as SpecKey[]) {
    params.delete(specParams[key]);
    if (query[key]) params.set(specParams[key], query[key]);
  }
  query.brands.forEach(brand => params.append('brand', brand));
  query.capacities.forEach(capacity => params.append('capacity', capacity));
  query.conditions.forEach(condition => params.append('condition', condition));
  query.stores.forEach(store => params.append('store', store));
  if (query.recentOnly) params.set('recent', '1');
  if (!query.inStockOnly) params.set('stock', 'all');
  if (query.sort !== defaultQuery().sort) params.set('sort', query.sort);
  if (query.days !== defaultQuery().days) params.set('days', String(query.days));
  return params.toString();
}
