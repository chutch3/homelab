import { describe, expect, it } from 'vitest';
import { along, rail, railBands, type RailMark } from '../../src/rail-marks';
import { checkedAt, makeDrive, makeOffer } from '../fixtures/listings';

const ago = (days: number) => new Date(checkedAt.getTime() - days * 86_400_000).toISOString();


const mark = (title: string, perTb: number, fields: Partial<RailMark> = {}): RailMark =>
  ({ key: `drive:${title}`, condition: 'new', title, capacityGb: 18000, perTb, lowest: false, ...fields });

describe('the rail the marks are drawn on', () => {
  it('runs between the round prices either side of every drive, in forty bands, each drive in the band its price falls in', () => {
    const drawn = rail([mark('Exos', 1000, { condition: 'manufacturer_recertified', lowest: true }), mark('Exos', 1600), mark('Gold', 1950)])!;
    expect([drawn.low, drawn.high, drawn.ticks]).toEqual([1000, 2000, [1000, 1200, 1400, 1600, 1800, 2000]]);
    expect(drawn.bands.map(band => [band.condition, band.index, Math.round(band.from), band.to && Math.round(band.to), band.drives, band.cheapest.title, band.lowest])).toEqual([
      ['manufacturer_recertified', 0, 1000, 1017, 1, 'Exos', true],
      ['new', 27, 1597, 1625, 1, 'Exos', false],
      ['new', 38, 1932, 1966, 1, 'Gold', false],
    ]);
  });

  it('gives each doubling of price the same room, so cheap drives are not crowded into a corner by dear ones', () => {
    const drawn = rail([mark('Cheap', 1000), mark('Dear', 16000)])!;
    expect([drawn.low, drawn.high]).toEqual([1000, 20000]);
    expect(along(drawn, 1000)).toBe(0);
    expect(along(drawn, 20000)).toBe(1);
    // $10 to $20 takes as much of the rail as $20 to $40.
    expect(along(drawn, 2000) - along(drawn, 1000)).toBeCloseTo(along(drawn, 4000) - along(drawn, 2000), 10);
    expect(drawn.ticks).toEqual([1000, 2000, 5000, 10000, 20000]);
  });

  it('gathers the drives of one condition whose prices share a band, cheapest named, and keeps conditions apart', () => {
    const drawn = rail([mark('A', 1000, { lowest: true }), mark('B', 1005), mark('C', 1010, { condition: 'used' }), mark('D', 2000)])!;
    expect(drawn.bands.map(band => [band.condition, band.drives, band.cheapest.title, band.lowest])).toEqual([
      ['new', 2, 'A', true], ['used', 1, 'C', false], ['new', 1, 'D', false],
    ]);
  });

  it('is drawn for one condition, or for all of them with the drives of every condition in a band counted together', () => {
    const drawn = rail([mark('A', 1000, { condition: 'used', lowest: true }), mark('B', 1005), mark('C', 1010, { condition: 'used' }), mark('D', 2000)])!;
    expect(railBands(drawn, null).map(band => [band.index, band.drives, band.cheapest.title, band.cheapest.condition, band.lowest]))
      .toEqual([[0, 3, 'A', 'used', true], [39, 1, 'D', 'new', false]]);
    expect(railBands(drawn, 'new').map(band => [band.index, band.drives, band.cheapest.title, band.lowest])).toEqual([[0, 1, 'B', false], [39, 1, 'D', false]]);
  });

  it('ends where all but the dearest hundredth of drives are, and gathers the rest past its end', () => {
    // Two hundred drives from $10.00 to $19.95, then two far dearer: a hundredth of 202, so both are past the rail's reach.
    const usual = Array.from({ length: 200 }, (_, index) => mark(`Drive ${index}`, 1000 + index * 5));
    const drawn = rail([...usual, mark('Tape', 63937500), mark('Dearer tape', 70000000, { condition: 'used' })])!;
    expect([drawn.low, drawn.high]).toEqual([1000, 2000]);
    expect(drawn.bands.filter(band => band.to === null).map(band => [band.condition, band.index, band.from, band.drives, band.cheapest.title]))
      .toEqual([['new', 40, 2000, 1, 'Tape'], ['used', 40, 2000, 1, 'Dearer tape']]);
    expect(drawn.bands.filter(band => band.to !== null)).toHaveLength(40);
  });

  it('is marked at each tenfold when prices are very far apart', () => {
    expect(rail([mark('Cheap', 119), mark('Tape', 63937500)])).toMatchObject({ low: 100, high: 80000000, ticks: [100, 1000, 10000, 100000, 1000000, 10000000] });
  });

  it('is nothing when no drive is in stock', () => {
    expect(rail([])).toBeNull();
  });
});
