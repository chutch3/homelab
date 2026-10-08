import { describe, expect, it } from 'vitest';
import { knownStores } from '../fixtures/listings';
import { entryDefaults, validateEntry, formFieldErrors, type EntryValues } from '../../src/entry-validation';

const valid: EntryValues = {
  title: 'Exos X18', mpn: 'ST18000NM000J', store: 'other', seller: 'Example seller', url: '', capacity: '18000',
  condition: 'refurbished', item: '189', shipping: '', inStock: true, observed: '2026-09-21T12:00', notes: '',
};

describe('entry validation', () => {
  it('leaves the title, URL, shipping & fees, and notes optional', () => {
    expect(validateEntry({ ...valid, title: '  ', url: '', shipping: '', notes: '' }, false)).toEqual({});
  });

  it('skips the item price only for an existing offer marked out of stock', () => {
    expect(validateEntry({ ...valid, item: '', inStock: false }, true)).toEqual({});
    expect(validateEntry({ ...valid, item: '', inStock: false }, false)).toEqual({ item: 'Enter the item price.' });
  });

  it('requires an item price', () => {
    expect(validateEntry({ ...valid, item: '  ' }, false)).toEqual({ item: 'Enter the item price.' });
    expect(validateEntry({ ...valid, item: '' }, true)).toEqual({ item: 'Enter the item price.' });
    // Nothing is sold for nothing; free shipping is another matter.
    expect(validateEntry({ ...valid, item: '0.00', shipping: '0' }, true)).toEqual({ item: 'Enter a price above zero.' });
  });

  it.each([
    ['title', 'x'.repeat(161), 'Use 160 characters or fewer.'],
    ['store', '', 'Choose a store.'],
    ['seller', 'x'.repeat(121), 'Use 120 characters or fewer.'],
    ['mpn', 'x'.repeat(101), 'Use 100 characters or fewer.'],
    ['mpn', '   ', 'Enter the MPN.'],
    ['condition', '', 'Choose a condition.'],
    ['notes', 'x'.repeat(2001), 'Use 2000 characters or fewer.'],
    ['capacity', '', 'Enter a capacity greater than zero.'],
    ['capacity', '0', 'Enter a capacity greater than zero.'],
    ['capacity', '-1', 'Enter a capacity greater than zero.'],
    ['capacity', '18.5', 'Enter whole gigabytes.'],
    ['capacity', '10000001', 'Enter 10,000,000 GB or less.'],
    ['url', 'example.com/disk', 'Enter an http:// or https:// URL.'],
    ['url', 'ftp://example.com/disk', 'Enter an http:// or https:// URL.'],
    ['url', 'https://example.com/' + 'x'.repeat(2083), 'Use 2083 characters or fewer.'],
    ['observed', '', 'Enter a valid observation date and time.'],
    ['observed', 'not a date', 'Enter a valid observation date and time.'],
    ['observed', '2026-02-30T12:00', 'Enter a valid observation date and time.'],
  ])('rejects invalid %s input (case %#)', (field, value, message) => {
    expect(validateEntry({ ...valid, [field]: value }, false)).toEqual({ [field]: message });
  });

  it("does not ask for a capacity when the MPN's drive already has one", () => {
    expect(validateEntry({ ...valid, capacity: '' }, false, true)).toEqual({});
  });

  it('ignores a seller name for a store that sells its own drives, since the form does not ask for one', () => {
    expect(validateEntry({ ...valid, store: 'goharddrive', seller: 'x'.repeat(121) }, false)).toEqual({});
  });

  it('requires the seller name for the Other store', () => {
    expect(validateEntry({ ...valid, store: 'other', seller: '  ' }, false))
      .toEqual({ seller: 'Name the seller when the store is Other.' });
  });

  it.each(['item', 'shipping'] as const)('validates %s with the same money rules', field => {
    expect(validateEntry({ ...valid, [field]: '-1' }, false)).toEqual({
      [field]: 'Enter a non-negative amount with up to two decimal places.',
    });
    expect(validateEntry({ ...valid, [field]: '10000000.01' }, false)).toEqual({
      [field]: 'Enter $10,000,000.00 or less.',
    });
  });

  it('accepts boundaries and trims text consistently with the API', () => {
    expect(validateEntry({
      ...valid, title: '  ' + 'x'.repeat(160) + '  ', mpn: 'x'.repeat(100),
      seller: 'x'.repeat(120), notes: 'x'.repeat(2000), capacity: '10000000',
      item: '10000000.00', url: 'https://example.com/disk', observed: '2024-02-29T12:30:59',
    }, false)).toEqual({});
  });

  it('validates only observation fields when recording a price', () => {
    expect(validateEntry({
      ...valid, title: '', seller: '', capacity: '', url: '', item: '-1',
    }, true)).toEqual({ item: 'Enter a non-negative amount with up to two decimal places.' });
  });
});

describe('API field errors', () => {
  it('maps offer and price errors to the new-offer inputs', () => {
    expect(formFieldErrors({
      mpn: 'Invalid MPN', store: 'Invalid store', capacity_gb: 'Invalid capacity', item_price_cents: 'Invalid amount',
      observed_at: 'Invalid time', 'unexpected.path': 'Other error',
    }, false)).toEqual({ mpn: 'Invalid MPN', store: 'Invalid store', capacity: 'Invalid capacity', item: 'Invalid amount', observed: 'Invalid time' });
  });

  it('maps observation errors without requiring listing inputs', () => {
    expect(formFieldErrors({ shipping_cents: 'Invalid shipping', notes: 'Too long' }, true))
      .toEqual({ shipping: 'Invalid shipping', notes: 'Too long' });
  });
});

describe('remembered entry defaults', () => {
  it.each([
    ['{"store":"goharddrive","condition":"refurbished"}', { store: 'goharddrive', condition: 'refurbished' }],
    ['{"store":"newegg","condition":"mint"}', { store: '', condition: '' }],
    ['not json', { store: '', condition: '' }],
    [null, { store: '', condition: '' }],
  ])('reads %s as a store and condition the form offers, or none', (stored, expected) => {
    expect(entryDefaults(stored, knownStores)).toEqual(expected);
  });
});
