import { describe, expect, it } from 'vitest';
import { defaultQuery, queryListings, readQuery, writeQuery, queryErrors } from '../../src/listing-query';
import { checkedAt, makeDrive, makeOffer, shoppingListings } from '../fixtures/listings';
import { emptySpecifications } from '../../src/specifications';

describe('listing filters and sorting', () => {
  const ids = (query = defaultQuery()) => queryListings(shoppingListings, query, checkedAt, 7).map(row => row.id);

  it('sorts by price per TB by default', () => {
    expect(ids()).toEqual(['Large drive', 'Small drive', 'Pricey drive']);
    expect(ids({ ...defaultQuery(), sort: 'total-desc' })).toEqual(['Pricey drive', 'Large drive', 'Small drive']);
  });
  it('filters a maximum total', () => {
    expect(ids({ ...defaultQuery(), maxTotal: '180' })).toEqual(['Small drive']);
  });
  it('keeps drives of any chosen capacity, combined with search', () => {
    expect(ids({ ...defaultQuery(), search: ' DRIVE ', capacities: ['12000', '18000'] })).toEqual(['Large drive', 'Small drive']);
  });
  it('searches MPN identifiers even when display names differ', () => {
    const rows = [makeOffer('Drive', { mpn: 'ST18000NM000J' })];
    expect(queryListings(rows, { ...defaultQuery(), search: 'st18000' }, checkedAt, 7)).toEqual(rows);
  });
  it('combines multiple conditions with seller', () => {
    const rows = [
      makeOffer('new'), makeOffer('used', { condition: 'used' }),
      makeOffer('refurbished', { condition: 'refurbished' }),
      makeOffer('other store', { store: 'goharddrive' }),
    ];
    const query = { ...defaultQuery(), conditions: ['new', 'used'], stores: ['other'] };
    expect(queryListings(rows, query, checkedAt, 7).map(row => row.id)).toEqual(['new', 'used']);
  });
  it('uses latest observation time and the configured recent window', () => {
    const rows = [
      makeOffer('recent'),
      makeOffer('boundary', {}, { observed_at: '2026-09-15T12:00:00Z' }),
      makeOffer('old', {}, { observed_at: '2026-09-15T11:59:59Z' }),
      makeOffer('future', {}, { observed_at: '2026-09-23T12:00:00Z' }),
    ];
    const query = { ...defaultQuery(), recentOnly: true };
    expect(queryListings(rows, query, checkedAt, 7).map(row => row.id)).toEqual(['boundary', 'recent']);
    expect(queryListings(rows, query, checkedAt, 1).map(row => row.id)).toEqual(['recent']);
  });
  it('does not mutate the input when sorting numerically', () => {
    const before = shoppingListings.map(row => row.id);
    expect(ids({ ...defaultQuery(), sort: 'capacity-desc' })).toEqual(['Pricey drive', 'Large drive', 'Small drive']);
    expect(shoppingListings.map(row => row.id)).toEqual(before);
  });
  it('reports invalid ranges and amounts rather than showing misleading results', () => {
    expect(queryErrors({ ...defaultQuery(), maxTotal: '-1' }).maxTotal).toBeTruthy();
    expect(ids({ ...defaultQuery(), maxTotal: '-1' })).toEqual([]);
  });
});


describe('ordering by when an offer was checked', () => {
  it('goes by the last check, not by when the price was first seen', () => {
    const rows = [
      makeOffer('rechecked today', { last_checked_at: '2026-09-22T09:00:00Z' }, { observed_at: '2026-01-01T00:00:00Z' }),
      makeOffer('seen last week', { last_checked_at: '2026-09-15T09:00:00Z' }, { observed_at: '2026-09-15T09:00:00Z' }),
    ];
    const ids = (sort: 'checked-asc' | 'checked-desc') => queryListings(rows, { ...defaultQuery(), sort }, checkedAt, 7).map(row => row.id);
    expect(ids('checked-desc')).toEqual(['rechecked today', 'seen last week']);
    expect(ids('checked-asc')).toEqual(['seen last week', 'rechecked today']);
    expect(readQuery('?sort=checked-desc').sort).toBe('checked-desc');
  });
});


describe('shopping view URL state', () => {
  it('ignores the retired SMR-management filter in a restored URL', () => {
    expect(readQuery('?recording=smr&smr=host_managed')).toEqual({ ...defaultQuery(), recording_type: 'smr' });
  });
  it('filters by plain specification values', () => {
    const drive = makeDrive('X', { specifications: { ...emptySpecifications(), interface: 'sata', recording_type: 'cmr', intended_use: ['nas'] } });
    const rows = [makeOffer('cmr', { drive }), makeOffer('unknown')];
    expect(queryListings(rows, { ...defaultQuery(), recording_type: 'cmr' }, checkedAt, 7).map(row => row.id)).toEqual(['cmr']);
    expect(queryListings(rows, { ...defaultQuery(), recording_type: 'unknown' }, checkedAt, 7).map(row => row.id)).toEqual(['unknown']);
    expect(queryListings(rows, { ...defaultQuery(), intended_use: 'nas' }, checkedAt, 7).map(row => row.id)).toEqual(['cmr']);
  });
  it('keeps drives of any chosen brand, unknown meaning no brand', () => {
    const rows = [makeOffer('seagate', { drive: makeDrive('A', { brand: 'Seagate' }) }), makeOffer('none', { drive: makeDrive('B') })];
    const kept = (brands: string[]) => queryListings(rows, { ...defaultQuery(), brands }, checkedAt, 7).map(row => row.id);
    expect(kept(['Seagate'])).toEqual(['seagate']);
    expect(kept(['unknown'])).toEqual(['none']);
    expect(kept([]).sort()).toEqual(['none', 'seagate']);
  });
  it('reports a total with more than two decimal places', () => {
    expect(queryErrors({ ...defaultQuery(), maxTotal: '1.005' }).maxTotal).toBe('Enter a non-negative number with up to two decimal places.');
  });
  it('round trips filters and sorting while preserving unrelated query parameters', () => {
    const query = { ...defaultQuery(), media_type: 'hdd', search: 'Exos', brands: ['Western Digital', 'unknown'], capacities: ['128', '20000'],
      maxTotal: '200', conditions: ['new', 'used'], stores: ['goharddrive', 'serverpartdeals'],
      recentOnly: true, inStockOnly: true, sort: 'total-desc' as const };
    const search = writeQuery(query, '?unrelated=keep');
    expect(readQuery(search)).toEqual(query);
    expect(new URLSearchParams(search).get('unrelated')).toBe('keep');
    expect(writeQuery(defaultQuery(), search)).toBe('unrelated=keep');
  });
  it('keeps the days the price range looks back over in the URL, unless they are the usual 90', () => {
    expect(defaultQuery().days).toBe(90);
    expect(readQuery('?days=30').days).toBe(30);
    expect(readQuery('?days=180').days).toBe(180);
    expect(readQuery('?days=45').days).toBe(90);
    expect(readQuery('?days=lots').days).toBe(90);
    expect(writeQuery({ ...defaultQuery(), days: 180 })).toBe('days=180');
    expect(writeQuery(defaultQuery(), '?days=30')).toBe('');
  });
  it('shows only offers in stock unless all are asked for, and says so in the URL only then', () => {
    expect(defaultQuery().inStockOnly).toBe(true);
    expect(readQuery('').inStockOnly).toBe(true);
    expect(readQuery('?stock=all').inStockOnly).toBe(false);
    expect(readQuery('?stock=1').inStockOnly).toBe(true);
    expect(writeQuery({ ...defaultQuery(), inStockOnly: false })).toBe('stock=all');
    expect(writeQuery(defaultQuery(), '?stock=all')).toBe('');
  });
  it('ignores unsupported sort and enum values', () => {
    expect(readQuery('?sort=nope&condition=nope&availability=in_stock&capacity=lots&capacity=-1')).toEqual(defaultQuery());
  });
});
