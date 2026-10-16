import type { Drive, Offer } from './api';

export const conditions = [
  { value: 'new', label: 'New' },
  { value: 'manufacturer_recertified', label: 'Recertified' },
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
export function sellerLabel({ store, store_name, seller }: Pick<Offer, 'store' | 'store_name' | 'seller'>): string {
  return store === 'other' ? seller : store_name;
}

/** What a row says of an offer collected with a capacity or title that may not be right, and why. */
export const doubts: Record<NonNullable<Offer['doubt']>, { label: string; why: string }> = {
  implausible_capacity: { label: 'Capacity unverified',
    why: 'Its capacity may have been misread from the store. It waits for a person to check it.' },
  not_a_single_drive: { label: 'May not be one drive',
    why: 'Its title reads as several drives, tape or other equipment. It waits for a person to check it.' },
};

const interfaces: Partial<Record<string, string>> = { sata: 'SATA', sas: 'SAS', nvme_pcie: 'NVMe', usb: 'USB' };
/** What a drive is, as a noun: by its form where that says more than its medium. */
function kindOf({ media_type, form_factor }: Drive['specifications']): string {
  if (form_factor === 'microsd') return 'microSD card';
  if (form_factor === 'sd') return 'SD card';
  return { hdd: 'hard drive', ssd: 'SSD', flash_card: 'flash card' }[media_type as string] ?? 'drive';
}

/** One name for a drive wherever it is shown, built from what is recorded of it: its maker, its
 * capacity, how it connects and what it is. Stores' own titles stay on their offers. */
export function driveName(drive: Drive): string {
  const connection = interfaces[drive.specifications.interface];
  return [drive.brand, capacityLabel(drive.capacity_gb), connection, kindOf(drive.specifications)].filter(Boolean).join(' ');
}
