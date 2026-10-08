import type { Store } from './api';
import { asksForSeller, conditions } from './listing-display';
import { parseDollars } from './money';

export type EntryValues = {
  title: string; mpn: string; store: string; seller: string; url: string; capacity: string;
  condition: string; item: string; shipping: string; inStock: boolean; observed: string; notes: string;
};

export function textError(value: string, limit: number, required?: string): string | null {
  const text = value.trim();
  if (!text && required) return required;
  return text.length > limit ? `Use ${limit} characters or fewer.` : null;
}

export function capacityError(value: string): string | null {
  const text = value.trim();
  const capacity = Number(text);
  if (!Number.isFinite(capacity) || capacity <= 0) return 'Enter a capacity greater than zero.';
  if (!/^\d+$/.test(text)) return 'Enter whole gigabytes.';
  return capacity > 10_000_000 ? 'Enter 10,000,000 GB or less.' : null;
}

export function urlError(value: string): string | null {
  const text = value.trim();
  if (!text) return null;
  if (text.length > 2083) return 'Use 2083 characters or fewer.';
  try {
    const url = new URL(text);
    if (['http:', 'https:'].includes(url.protocol) && url.hostname) return null;
  } catch { /* Report the same actionable error for malformed URLs and unsupported schemes. */ }
  return 'Enter an http:// or https:// URL.';
}

function validLocalDate(value: string): boolean {
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!parts) return false;
  const [year, month, day, hour, minute, second] = parts.slice(1).map(part => Number(part ?? 0));
  const date = new Date(value);
  return year > 0 && date.getFullYear() === year && date.getMonth() + 1 === month
    && date.getDate() === day && date.getHours() === hour && date.getMinutes() === minute
    && date.getSeconds() === second;
}

export function validateEntry(values: EntryValues, priceOnly: boolean, capacityKnown = false): Record<string, string> {
  const errors: Record<string, string> = {};
  const check = (field: keyof EntryValues, message: string | null) => {
    if (message) errors[field] = message;
  };
  if (!priceOnly) {
    check('title', textError(values.title, 160));
    check('mpn', textError(values.mpn, 100, 'Enter the MPN.'));
    if (!capacityKnown) check('capacity', capacityError(values.capacity));
    check('store', values.store ? null : 'Choose a store.');
    if (asksForSeller(values.store)) check('seller', textError(values.seller, 120, values.store === 'other' ? 'Name the seller when the store is Other.' : undefined));
    check('url', urlError(values.url));
    check('condition', values.condition ? null : 'Choose a condition.');
  }
  for (const field of ['item', 'shipping'] as const) {
    try {
      // Nothing is sold for nothing; shipping can be free.
      if (parseDollars(values[field]) === 0 && field === 'item') errors.item = 'Enter a price above zero.';
    } catch (error) { errors[field] = (error as Error).message; }
  }
  if (!values.item.trim() && (values.inStock || !priceOnly)) errors.item = 'Enter the item price.';
  check('observed', validLocalDate(values.observed) ? null : 'Enter a valid observation date and time.');
  check('notes', textError(values.notes, 2000));
  return errors;
}

const listingFields: Record<string, keyof EntryValues> = {
  title: 'title', mpn: 'mpn', store: 'store', capacity_gb: 'capacity', seller: 'seller',
  url: 'url', condition: 'condition',
};
const observationFields: Record<string, keyof EntryValues> = {
  item_price_cents: 'item', shipping_cents: 'shipping', observed_at: 'observed', notes: 'notes',
};

export function formFieldErrors(fields: Record<string, string>, priceOnly: boolean): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [path, message] of Object.entries(fields)) {
    let field: keyof EntryValues | undefined;
    field = observationFields[path] ?? (priceOnly ? undefined : listingFields[path]);
    if (field) errors[field] = message;
  }
  return errors;
}

export type EntryDefaults = { store: string; condition: string };

/** The store and condition last used for a new offer, as stored; anything the form no
 * longer offers, or that cannot be read, starts blank. */
export function entryDefaults(stored: string | null, stores: Store[]): EntryDefaults {
  let saved: Partial<EntryDefaults> = {};
  try { saved = JSON.parse(stored ?? '{}') ?? {}; } catch { /* Unreadable: start blank. */ }
  return {
    store: stores.some(store => store.key === saved.store) ? saved.store! : '',
    condition: conditions.some(option => option.value === saved.condition) ? saved.condition! : '',
  };
}
