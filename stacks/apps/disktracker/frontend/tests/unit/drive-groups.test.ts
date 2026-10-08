import { describe, expect, it } from 'vitest';
import { groupByDrive, knownDrives } from '../../src/drive-groups';
import { makeDrive, makeListing } from '../fixtures/listings';

describe('grouping listings by drive', () => {
  it('groups listings that share a drive and keeps unconfirmed listings separate', () => {
    const drive = makeDrive('ST18000NM000J');
    const a = makeListing('Seller A', { drive, seller: 'Seller A' });
    const b = makeListing('Seller B', { drive, seller: 'Seller B' });
    const unconfirmed = makeListing('No MPN yet');
    const groups = groupByDrive([a, b, unconfirmed], 'unit-asc');
    expect(groups).toHaveLength(2);
    const shared = groups.find(group => group.drive?.id === drive.id)!;
    expect(shared.listings.map(listing => listing.id).sort()).toEqual(['Seller A', 'Seller B']);
    const alone = groups.find(group => group.drive === null)!;
    expect(alone.listings).toEqual([unconfirmed]);
  });

  it('picks the cheapest listing in a group as its representative when sorting by $/TB', () => {
    const drive = makeDrive('ST18000NM000J');
    const cheaper = makeListing('Cheaper', { drive }, { total_cents: 20000, price_per_tb: '10.00' });
    const pricier = makeListing('Pricier', { drive }, { total_cents: 30000, price_per_tb: '15.00' });
    const [group] = groupByDrive([pricier, cheaper], 'unit-asc');
    expect(group.representative.id).toBe('Cheaper');
  });

  it("shows a drive's cheapest offer whichever way the list is ordered", () => {
    const drive = makeDrive('ST18000NM000J');
    const cheaper = makeListing('Cheaper', { drive }, { total_cents: 20000, price_per_tb: '10.00' });
    const pricier = makeListing('Pricier', { drive }, { total_cents: 30000, price_per_tb: '15.00' });
    for (const sort of ['unit-desc', 'total-desc', 'checked-asc', 'capacity-asc'] as const) {
      expect(groupByDrive([pricier, cheaper], sort)[0].representative.id).toBe('Cheaper');
    }
  });

  it('prefers an in-stock listing as the representative even when a sold-out one is cheaper', () => {
    const drive = makeDrive('ST18000NM000J');
    const soldOut = makeListing('Sold out', { drive }, { total_cents: 20000, price_per_tb: '10.00', in_stock: false });
    const stocked = makeListing('Stocked', { drive }, { total_cents: 30000, price_per_tb: '15.00' });
    const [group] = groupByDrive([soldOut, stocked], 'unit-asc');
    expect(group.representative.id).toBe('Stocked');
  });

  it('orders groups by their representative, matching the chosen sort', () => {
    const cheap = makeListing('Cheap', {}, { total_cents: 10000, price_per_tb: '5.00' });
    const pricey = makeListing('Pricey', {}, { total_cents: 40000, price_per_tb: '20.00' });
    expect(groupByDrive([pricey, cheap], 'unit-asc').map(group => group.key)).toEqual(
      groupByDrive([cheap, pricey], 'unit-asc').map(group => group.key),
    );
    const ascending = groupByDrive([pricey, cheap], 'unit-asc').map(group => group.representative.id);
    expect(ascending).toEqual(['Cheap', 'Pricey']);
    const descending = groupByDrive([pricey, cheap], 'unit-desc').map(group => group.representative.id);
    expect(descending).toEqual(['Pricey', 'Cheap']);
  });
});

describe('drives already known', () => {
  it('are each drive once, by MPN, named by a listing title, leaving out offers with no drive', () => {
    const exos = makeDrive('ST18000NM000J');
    const listings = [
      makeListing('Exos X18 at store B', { drive: exos }), makeListing('Exos X18', { drive: exos }),
      makeListing('Red', { drive: makeDrive('WD120EFBX') }), makeListing('no drive'),
    ];
    expect(knownDrives(listings)).toEqual([
      { mpn: 'ST18000NM000J', title: 'Exos X18 at store B' }, { mpn: 'WD120EFBX', title: 'Red' },
    ]);
  });
});
