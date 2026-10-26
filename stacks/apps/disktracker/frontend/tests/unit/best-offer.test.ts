import { expect, it } from 'vitest';
import { bestOffer } from '../../src/best-offer';
import { makeOffer } from '../fixtures/listings';

it('picks the lowest total', () => {
  const cheapTotal = makeOffer('cheap-total', {}, { item_price_cents: 46000, total_cents: 48700 });
  const cheapItem = makeOffer('cheap-item', {}, { item_price_cents: 45000, total_cents: 49900 });
  expect(bestOffer([cheapItem, cheapTotal])).toEqual({ listing: cheapTotal, price: 48700 });
});

it('returns null when there are no listings', () => {
  expect(bestOffer([])).toBeNull();
});

it('never picks a sold-out offer, and returns null when every offer is sold out', () => {
  const soldOut = makeOffer('sold', {}, { total_cents: 100, in_stock: false });
  const stocked = makeOffer('stocked', {}, { total_cents: 900 });
  expect(bestOffer([soldOut, stocked])?.listing.id).toBe('stocked');
  expect(bestOffer([soldOut])).toBeNull();
});

it('never picks an offer that may not be one drive of its capacity', () => {
  const doubted = makeOffer('bundle', { doubt: 'not_a_single_drive' }, { total_cents: 100 });
  const drive = makeOffer('drive', {}, { total_cents: 900 });
  expect(bestOffer([doubted, drive])?.listing.id).toBe('drive');
  expect(bestOffer([doubted])).toBeNull();
});
