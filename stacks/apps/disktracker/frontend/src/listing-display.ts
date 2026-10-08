import type { Listing } from './api';

export const conditions = [
  { value: 'new', label: 'New' },
  { value: 'manufacturer_recertified', label: 'Manufacturer recertified' },
  { value: 'refurbished', label: 'Refurbished' },
  { value: 'used', label: 'Used' },
];
export const conditionLabel = (value: string) => conditions.find(c => c.value === value)?.label ?? value;
/** Capacities are whole decimal gigabytes (1 TB = 1000 GB), shown in TB from one terabyte up. */
export const capacityLabel = (gigabytes: number) =>
  gigabytes < 1000 ? `${gigabytes} GB` : `${Number((gigabytes / 1000).toFixed(3))} TB`;
export const dollars = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value / 100);

/** Stores sell their own stock; Other is a one-off store, named by its seller. */
export const asksForSeller = (store: string) => store === 'other';
export function sellerLabel({ store, store_name, seller }: Pick<Listing, 'store' | 'store_name' | 'seller'>): string {
  return store === 'other' ? seller : store_name;
}
