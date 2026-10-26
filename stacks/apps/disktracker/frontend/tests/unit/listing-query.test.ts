import { describe, expect, it } from 'vitest';
import { defaultQuery, readQuery, writeQuery, queryErrors } from '../../src/listing-query';

describe('listing filters', () => {
  it('reports invalid ranges and amounts rather than showing misleading results', () => {
    expect(queryErrors({ ...defaultQuery(), maxTotal: '-1' }).maxTotal).toBeTruthy();
  });
});

describe('shopping view URL state', () => {
  it('keeps the order by last check', () => {
    expect(readQuery('?sort=checked-desc').sort).toBe('checked-desc');
  });
  it('ignores the retired SMR-management filter in a restored URL', () => {
    expect(readQuery('?recording=smr&smr=host_managed')).toEqual({ ...defaultQuery(), recording_type: 'smr' });
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
