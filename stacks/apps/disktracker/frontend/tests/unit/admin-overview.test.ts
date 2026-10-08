import { describe, expect, it } from 'vitest';
import { ageLabel, driveIssues, elapsedLabel, freshness, issues, overdueForRecheck } from '../../src/admin-overview';
import { groupByDrive } from '../../src/drive-groups';
import { emptySpecifications } from '../../src/specifications';
import { checkedAt, knownStores, makeDrive, makeListing } from '../fixtures/listings';

const hours = (count: number) => new Date(checkedAt.getTime() - count * 3_600_000).toISOString();

describe('what needs attention for a drive', () => {
  const issuesOf = (listings: ReturnType<typeof makeListing>[]) =>
    driveIssues(groupByDrive(listings, 'unit-asc')[0], checkedAt, 7);

  it('flags a drive with no known specification or an in-stock offer not checked recently', () => {
    const drive = makeDrive('A');
    expect(issuesOf([makeListing('a', { drive, last_checked_at: hours(24 * 8) })]))
      .toEqual(['unknown_specifications', 'stale']);
  });

  it('does not count a single store selling a drive: there is nothing to do about it', () => {
    const drive = makeDrive('A', { specifications: { ...emptySpecifications(), intended_use: ['nas'] } });
    expect(issuesOf([makeListing('a', { drive })])).toEqual([]);
    expect(issues).toEqual(['unknown_specifications', 'stale']);
  });

  it('flags nothing for a known drive two stores sell and check', () => {
    const drive = makeDrive('A', { specifications: { ...emptySpecifications(), intended_use: ['nas'] } });
    expect(issuesOf([makeListing('a', { drive, seller: 'One' }), makeListing('b', { drive, seller: 'Two' })])).toEqual([]);
  });

  it('does not call a sold-out offer stale: it is not expected to change', () => {
    const drive = makeDrive('A', { specifications: { ...emptySpecifications(), interface: 'sas' } });
    const soldOut = makeListing('a', { drive, seller: 'One', last_checked_at: hours(24 * 30) }, { in_stock: false });
    expect(issuesOf([soldOut, makeListing('b', { drive, seller: 'Two' })])).toEqual([]);
  });
});

describe('price freshness', () => {
  it("gives each store's offer count, latest check, and median age, stores in the usual order", () => {
    const listings = [
      makeListing('o', { store: 'other', seller: 'Micro Center', last_checked_at: hours(1) }),
      makeListing('s1', { store: 'serverpartdeals', seller: '', last_checked_at: hours(0) }),
      makeListing('s2', { store: 'serverpartdeals', seller: '', last_checked_at: hours(10) }),
      makeListing('s3', { store: 'serverpartdeals', seller: '', last_checked_at: hours(30) }),
    ];
    expect(freshness(listings, checkedAt, knownStores)).toEqual([
      { store: knownStores[0], offers: 3, latest: hours(0), medianAgeMs: 10 * 3_600_000 },
      { store: knownStores[3], offers: 1, latest: hours(1), medianAgeMs: 3_600_000 },
    ]);
  });
});

it.each([[30 * 60_000, 'under an hour'], [3_600_000, '1 hour'], [5 * 3_600_000, '5 hours'],
  [47 * 3_600_000, '47 hours'], [48 * 3_600_000, '2 days'], [5 * 86_400_000, '5 days']])(
  'says an age of %i ms as "%s"', (age, label) => {
    expect(ageLabel(age)).toBe(label);
  },
);

describe('offers overdue for a recheck', () => {
  it('are hand-entered offers last checked before the recent window, oldest first', () => {
    const checked = (id: string, age: number, method = 'manual') =>
      makeListing(id, { last_checked_at: hours(age) }, { acquisition_method: method });
    const listings = [
      checked('eight days', 24 * 8), checked('exactly seven days', 24 * 7), checked('today', 1),
      checked('thirty days', 24 * 30), checked('collected', 24 * 40, 'serverpartdeals'),
    ];
    expect(overdueForRecheck(listings, checkedAt, 7).map(listing => listing.id)).toEqual(['thirty days', 'eight days']);
    expect(overdueForRecheck([], checkedAt, 7)).toEqual([]);
  });
});

it.each([[20_000, 'under a minute'], [60_000, '1 minute'], [20 * 60_000, '20 minutes'], [59 * 60_000, '59 minutes'],
  [3_600_000, '1 hour'], [125 * 60_000, '2 hours'], [47 * 3_600_000, '47 hours'], [48 * 3_600_000, '2 days']])(
  'says %i ms elapsed as "%s", to the minute within the hour', (elapsed, label) => {
    expect(elapsedLabel(elapsed)).toBe(label);
  },
);
