import { emptySpecifications, matchesSpecification, specOptions, type SpecKey } from './specifications';
import type { Condition, ListingSummary } from './api';
import { conditions, sellerLabel } from './listing-display';

export const sorts = [
  { value: 'unit-asc', label: '$/TB: low to high' }, { value: 'unit-desc', label: '$/TB: high to low' },
  { value: 'total-asc', label: 'Total: low to high' }, { value: 'total-desc', label: 'Total: high to low' },
  { value: 'capacity-asc', label: 'Capacity: low to high' }, { value: 'capacity-desc', label: 'Capacity: high to low' },
  { value: 'checked-desc', label: 'Checked most recently' }, { value: 'checked-asc', label: 'Checked longest ago' },
] as const;
export type Sort = typeof sorts[number]['value'];
export type ListingQuery = {
  media_type: string; form_factor: string; interface: string; intended_use: string; recording_type: string;
  search: string; brands: string[]; capacities: string[]; maxTotal: string;
  conditions: string[]; stores: string[]; recentOnly: boolean; inStockOnly: boolean; sort: Sort;
};
export const defaultQuery = (): ListingQuery => ({
  media_type: '', form_factor: '', interface: '', intended_use: '', recording_type: '',
  search: '', brands: [], capacities: [], maxTotal: '', conditions: [], stores: [],
  recentOnly: false, inStockOnly: false, sort: 'unit-asc',
});
const DAY = 86_400_000;

export function isRecent(listing: ListingSummary, now: Date, days: number): boolean {
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

export function queryListings(listings: ListingSummary[], query: ListingQuery, now: Date, recentDays: number): ListingSummary[] {
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

const driveKey = (listing: ListingSummary) => listing.drive?.id ?? `listing:${listing.id}`;

/** Every brand the loaded drives come in, most drives first, then drives of no known brand. */
export function brandCounts(listings: ListingSummary[]): BrandCount[] {
  const drives = new Map<string, Set<string>>();
  for (const listing of listings) {
    const brand = listing.drive?.brand ?? UNKNOWN_BRAND;
    drives.set(brand, (drives.get(brand) ?? new Set()).add(driveKey(listing)));
  }
  const counts = [...drives].map(([brand, keys]) => ({ brand, drives: keys.size }));
  const known = counts.filter(count => count.brand !== UNKNOWN_BRAND)
    .sort((a, b) => b.drives - a.drives || a.brand.localeCompare(b.brand));
  return [...known, ...counts.filter(count => count.brand === UNKNOWN_BRAND)];
}

export type ConditionCount = { condition: Condition; drives: number };

/** Every condition the loaded drives are sold in, in the usual order, with how many drives are. */
export function conditionCounts(listings: ListingSummary[]): ConditionCount[] {
  return conditions.flatMap(({ value }) => {
    const drives = new Set(listings.filter(listing => listing.condition === value).map(driveKey)).size;
    return drives ? [{ condition: value as Condition, drives }] : [];
  });
}

export type CapacityCount = { capacity_gb: number; drives: number };

/** Every capacity the loaded drives come in, smallest first, with how many drives have it. */
export function capacityCounts(listings: ListingSummary[]): CapacityCount[] {
  const drives = new Map<number, Set<string>>();
  for (const listing of listings) {
    drives.set(listing.capacity_gb, (drives.get(listing.capacity_gb) ?? new Set()).add(driveKey(listing)));
  }
  return [...drives].sort(([a], [b]) => a - b).map(([capacity_gb, keys]) => ({ capacity_gb, drives: keys.size }));
}

export function sortValue(sort: Sort, listing: ListingSummary): number | null {
  const column = sort.split('-')[0];
  if (column === 'capacity') return listing.capacity_gb;
  if (column === 'checked') return Date.parse(listing.last_checked_at);
  if (column === 'total') return listing.latest.total_cents;
  return listing.latest.price_per_tb === null ? null : Number(listing.latest.price_per_tb);
}

export function compareListings(sort: Sort): (a: ListingSummary, b: ListingSummary) => number {
  const direction = sort.split('-')[1];
  return (a, b) => {
    const left = sortValue(sort, a), right = sortValue(sort, b);
    if (left === null && right !== null) return 1;
    if (right === null && left !== null) return -1;
    const difference = left === null || right === null ? 0 : (left - right) * (direction === 'asc' ? 1 : -1);
    return difference || a.id.localeCompare(b.id);
  };
}

export function priceLeaders(listings: ListingSummary[], now: Date, days: number): { total: Set<string>; unit: Set<string> } {
  const eligible = listings.filter(listing => listing.latest.in_stock && isRecent(listing, now, days));
  const lowestTotal = Math.min(...eligible.map(listing => listing.latest.total_cents!));
  const lowestUnit = Math.min(...eligible.map(listing => Number(listing.latest.price_per_tb)));
  return {
    total: new Set(eligible.filter(listing => listing.latest.total_cents === lowestTotal).map(listing => listing.id)),
    unit: new Set(eligible.filter(listing => Number(listing.latest.price_per_tb) === lowestUnit).map(listing => listing.id)),
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
  query.inStockOnly = params.get('stock') === '1';
  const sort = params.get('sort');
  if (sorts.some(option => option.value === sort)) query.sort = sort as Sort;
  return query;
}
export function writeQuery(query: ListingQuery, current = ''): string {
  const params = new URLSearchParams(current);
  for (const [field, parameter] of Object.entries(textParams)) {
    params.delete(parameter);
    const value = query[field as keyof typeof textParams];
    if (value) params.set(parameter, value);
  }
  for (const parameter of ['brand', 'capacity', 'condition', 'store', 'recent', 'stock', 'sort']) params.delete(parameter);
  for (const key of Object.keys(specParams) as SpecKey[]) {
    params.delete(specParams[key]);
    if (query[key]) params.set(specParams[key], query[key]);
  }
  query.brands.forEach(brand => params.append('brand', brand));
  query.capacities.forEach(capacity => params.append('capacity', capacity));
  query.conditions.forEach(condition => params.append('condition', condition));
  query.stores.forEach(store => params.append('store', store));
  if (query.recentOnly) params.set('recent', '1');
  if (query.inStockOnly) params.set('stock', '1');
  if (query.sort !== defaultQuery().sort) params.set('sort', query.sort);
  return params.toString();
}
