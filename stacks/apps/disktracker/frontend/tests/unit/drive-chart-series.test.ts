import { describe, expect, it } from 'vitest';
import { driveChartSeries } from '../../src/drive-chart-series';
import { makeDrive, makeListing } from '../fixtures/listings';

describe('building one chart series per listing sharing a drive', () => {
  it('gives each offer its own series named by its store, colored in a fixed order', () => {
    const drive = makeDrive('ST18000NM000J');
    const a = makeListing('b-seller', { drive, store: 'goharddrive', seller: '', condition: 'refurbished' });
    const c = makeListing('a-seller', { drive, store: 'other', seller: 'Seller A', condition: 'new' });
    const series = driveChartSeries([a, c]);
    expect(series.map(s => s.listingId)).toEqual(['a-seller', 'b-seller']);
    expect(series.map(s => s.label)).toEqual(['Seller A', 'GoHardDrive']);
    expect(new Set(series.map(s => s.color)).size).toBe(2);
  });

  it('caps distinct colors at three and folds additional sellers into a shared "Other" color', () => {
    const drive = makeDrive('ST18000NM000J');
    const listings = ['a', 'b', 'c', 'd', 'e'].map(id => makeListing(id, { drive, seller: id }));
    const series = driveChartSeries(listings);
    const colors = series.map(s => s.color);
    expect(new Set(colors.slice(0, 3)).size).toBe(3);
    expect(colors[3]).toBe(colors[4]);
    expect(colors[3]).not.toBe(colors[0]);
  });

  it('excludes listings with no observations', () => {
    const drive = makeDrive('ST18000NM000J');
    const priced = makeListing('priced', { drive, seller: 'Priced seller' });
    const unpriced = makeListing('unpriced', { drive, seller: 'Unpriced seller', observations: [] });
    const series = driveChartSeries([priced, unpriced]);
    expect(series.map(s => s.listingId)).toEqual(['priced']);
  });
});
