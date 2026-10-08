import { expect, it } from 'vitest';
import { asksForSeller, capacityLabel, sellerLabel } from '../../src/listing-display';

it('names an offer by its store', () => {
  expect(sellerLabel({ store: 'serverorbit', store_name: 'ServerOrbit', seller: '' })).toBe('ServerOrbit');
});

it('names an Other offer by its store name alone', () => {
  expect(sellerLabel({ store: 'other', store_name: 'Other', seller: 'Micro Center' })).toBe('Micro Center');
});

it('asks for a store name only for Other', () => {
  expect(['serverpartdeals', 'serverorbit', 'other'].filter(asksForSeller)).toEqual(['other']);
});

it.each([[18000, '18 TB'], [1920, '1.92 TB'], [1000, '1 TB'], [960, '960 GB'], [32, '32 GB']])(
  'labels %i GB as %s, switching to TB from one terabyte up', (gigabytes, label) => {
    expect(capacityLabel(gigabytes)).toBe(label);
  });
