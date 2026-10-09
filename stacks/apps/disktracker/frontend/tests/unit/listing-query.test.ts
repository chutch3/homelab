import { describe, expect, it } from 'vitest';
import { brandCounts, capacityCounts, conditionCounts, defaultQuery, queryListings, priceLeaders, readQuery, writeQuery, queryErrors } from '../../src/listing-query';
import { checkedAt, makeDrive, makeListing, shoppingListings } from '../fixtures/listings';
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
    const rows = [makeListing('Drive', { mpn: 'ST18000NM000J' })];
    expect(queryListings(rows, { ...defaultQuery(), search: 'st18000' }, checkedAt, 7)).toEqual(rows);
  });
  it('combines multiple conditions with seller', () => {
    const rows = [
      makeListing('new'), makeListing('used', { condition: 'used' }),
      makeListing('refurbished', { condition: 'refurbished' }),
      makeListing('other store', { store: 'goharddrive' }),
    ];
    const query = { ...defaultQuery(), conditions: ['new', 'used'], stores: ['other'] };
    expect(queryListings(rows, query, checkedAt, 7).map(row => row.id)).toEqual(['new', 'used']);
  });
  it('uses latest observation time and the configured recent window', () => {
    const rows = [
      makeListing('recent'),
      makeListing('boundary', {}, { observed_at: '2026-09-15T12:00:00Z' }),
      makeListing('old', {}, { observed_at: '2026-09-15T11:59:59Z' }),
      makeListing('future', {}, { observed_at: '2026-09-23T12:00:00Z' }),
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

describe('the conditions drives are sold in', () => {
  it('are those with an offer, in the usual order, each with how many drives are sold in it', () => {
    const drive = makeDrive('A');
    const rows = [
      makeListing('a-used', { drive, condition: 'used' }), makeListing('a-new', { drive, condition: 'new', seller: 'One' }),
      makeListing('a-new-too', { drive, condition: 'new', seller: 'Two' }), makeListing('b-new', { drive: makeDrive('B'), condition: 'new' }),
    ];
    expect(conditionCounts(rows)).toEqual([{ condition: 'new', drives: 2 }, { condition: 'used', drives: 1 }]);
    expect(conditionCounts([])).toEqual([]);
  });
});

describe('ordering by when an offer was checked', () => {
  it('goes by the last check, not by when the price was first seen', () => {
    const rows = [
      makeListing('rechecked today', { last_checked_at: '2026-09-22T09:00:00Z' }, { observed_at: '2026-01-01T00:00:00Z' }),
      makeListing('seen last week', { last_checked_at: '2026-09-15T09:00:00Z' }, { observed_at: '2026-09-15T09:00:00Z' }),
    ];
    const ids = (sort: 'checked-asc' | 'checked-desc') => queryListings(rows, { ...defaultQuery(), sort }, checkedAt, 7).map(row => row.id);
    expect(ids('checked-desc')).toEqual(['rechecked today', 'seen last week']);
    expect(ids('checked-asc')).toEqual(['seen last week', 'rechecked today']);
    expect(readQuery('?sort=checked-desc').sort).toBe('checked-desc');
  });
});

describe('current price leaders', () => {
  it('keeps ties and excludes prices not checked recently', () => {
    const rows = [
      makeListing('a'), makeListing('b'),
      makeListing('old', {}, { total_cents: 1, price_per_tb: '0.01', observed_at: '2026-01-01T00:00:00Z' }),
    ];
    const result = priceLeaders(rows, checkedAt, 7);
    expect([...result.total]).toEqual(['a', 'b']);
    expect([...result.unit]).toEqual(['a', 'b']);
  });
  it('never labels a sold-out offer as the lowest', () => {
    const rows = [makeListing('sold', {}, { total_cents: 1, price_per_tb: '0.01', in_stock: false }), makeListing('stocked')];
    const result = priceLeaders(rows, checkedAt, 7);
    expect([...result.total]).toEqual(['stocked']);
    expect([...result.unit]).toEqual(['stocked']);
  });
  it('treats an offer as recent when it was checked recently, even if its price is older', () => {
    const rechecked = makeListing('rechecked', { last_checked_at: '2026-09-21T12:00:00Z' }, { observed_at: '2026-01-01T00:00:00Z' });
    expect(priceLeaders([rechecked], checkedAt, 7).total).toEqual(new Set(['rechecked']));
  });
  it('finds separate total-cost and per-TB winners within the matching rows', () => {
    const result = priceLeaders(shoppingListings, checkedAt, 7);
    expect([...result.total]).toEqual(['Small drive']);
    expect([...result.unit]).toEqual(['Large drive']);
  });
});

describe('shopping view URL state', () => {
  it('ignores the retired SMR-management filter in a restored URL', () => {
    expect(readQuery('?recording=smr&smr=host_managed')).toEqual({ ...defaultQuery(), recording_type: 'smr' });
  });
  it('filters by plain specification values', () => {
    const drive = makeDrive('X', { specifications: { ...emptySpecifications(), interface: 'sata', recording_type: 'cmr', intended_use: ['nas'] } });
    const rows = [makeListing('cmr', { drive }), makeListing('unknown')];
    expect(queryListings(rows, { ...defaultQuery(), recording_type: 'cmr' }, checkedAt, 7).map(row => row.id)).toEqual(['cmr']);
    expect(queryListings(rows, { ...defaultQuery(), recording_type: 'unknown' }, checkedAt, 7).map(row => row.id)).toEqual(['unknown']);
    expect(queryListings(rows, { ...defaultQuery(), intended_use: 'nas' }, checkedAt, 7).map(row => row.id)).toEqual(['cmr']);
  });
  it('lists each capacity loaded, smallest first, with how many drives have it', () => {
    const shared = makeDrive('A');
    const rows = [
      makeListing('a1', { drive: shared, capacity_gb: 18000 }), makeListing('a2', { drive: shared, capacity_gb: 18000 }),
      makeListing('b', { drive: makeDrive('B'), capacity_gb: 18000 }), makeListing('card', { capacity_gb: 128 }),
    ];
    expect(capacityCounts(rows)).toEqual([{ capacity_gb: 128, drives: 1 }, { capacity_gb: 18000, drives: 2 }]);
    expect(capacityCounts([])).toEqual([]);
  });
  it('lists each brand loaded by how many drives it has, most first, with drives of no known brand last as unknown', () => {
    const rows = [
      makeListing('a', { drive: makeDrive('A', { brand: 'Toshiba' }) }),
      makeListing('b', { drive: makeDrive('B', { brand: 'Seagate' }) }), makeListing('c', { drive: makeDrive('C', { brand: 'Seagate' }) }),
      makeListing('d', { drive: makeDrive('D') }), makeListing('no drive'),
    ];
    expect(brandCounts(rows)).toEqual([
      { brand: 'Seagate', drives: 2 }, { brand: 'Toshiba', drives: 1 }, { brand: 'unknown', drives: 2 },
    ]);
    expect(brandCounts([])).toEqual([]);
  });
  it('keeps drives of any chosen brand, unknown meaning no brand', () => {
    const rows = [makeListing('seagate', { drive: makeDrive('A', { brand: 'Seagate' }) }), makeListing('none', { drive: makeDrive('B') })];
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
  it('ignores unsupported sort and enum values', () => {
    expect(readQuery('?sort=nope&condition=nope&availability=in_stock&capacity=lots&capacity=-1')).toEqual(defaultQuery());
  });
});
