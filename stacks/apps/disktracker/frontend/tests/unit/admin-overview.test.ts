import { describe, expect, it } from 'vitest';
import { ageLabel, driveIssues, elapsedLabel, freshness, issues } from '../../src/admin-overview';
import { groupByDrive } from '../../src/drive-groups';
import { emptySpecifications } from '../../src/specifications';
import { checkedAt, knownStores, makeDrive, makeOffer } from '../fixtures/listings';

const hours = (count: number) => new Date(checkedAt.getTime() - count * 3_600_000).toISOString();

describe('what needs attention for a drive', () => {
  const issuesOf = (listings: ReturnType<typeof makeOffer>[]) =>
    driveIssues(groupByDrive(listings, 'unit-asc')[0], checkedAt, 7);

  it('flags a drive with no known specification or an in-stock offer not checked recently', () => {
    const drive = makeDrive('A');
    expect(issuesOf([makeOffer('a', { drive, last_checked_at: hours(24 * 8) })]))
      .toEqual(['unknown_specifications', 'stale']);
  });

  it('does not count a single store selling a drive: there is nothing to do about it', () => {
    const drive = makeDrive('A', { specifications: { ...emptySpecifications(), intended_use: ['nas'] } });
    expect(issuesOf([makeOffer('a', { drive })])).toEqual([]);
    expect(issues).toEqual(['unknown_specifications', 'stale']);
  });

  it('flags nothing for a known drive two stores sell and check', () => {
    const drive = makeDrive('A', { specifications: { ...emptySpecifications(), intended_use: ['nas'] } });
    expect(issuesOf([makeOffer('a', { drive, seller: 'One' }), makeOffer('b', { drive, seller: 'Two' })])).toEqual([]);
  });

  it('does not call a sold-out offer stale: it is not expected to change', () => {
    const drive = makeDrive('A', { specifications: { ...emptySpecifications(), interface: 'sas' } });
    const soldOut = makeOffer('a', { drive, seller: 'One', last_checked_at: hours(24 * 30) }, { in_stock: false });
    expect(issuesOf([soldOut, makeOffer('b', { drive, seller: 'Two' })])).toEqual([]);
  });
});

describe('price freshness', () => {
  it("gives each store's offer count, latest check, and median age, stores in the usual order", () => {
    const listings = [
      makeOffer('o', { store: 'other', seller: 'Micro Center', last_checked_at: hours(1) }),
      makeOffer('s1', { store: 'serverpartdeals', seller: '', last_checked_at: hours(0) }),
      makeOffer('s2', { store: 'serverpartdeals', seller: '', last_checked_at: hours(10) }),
      makeOffer('s3', { store: 'serverpartdeals', seller: '', last_checked_at: hours(30) }),
    ];
    expect(freshness(listings, checkedAt, knownStores)).toEqual([
      { store: knownStores[0], offers: 3, latest: hours(0), medianAgeMs: 10 * 3_600_000 },
      { store: knownStores[3], offers: 1, latest: hours(1), medianAgeMs: 3_600_000 },
    ]);
  });
});

it.each([[30 * 60_000, '<1h'], [3_600_000, '1h'], [5 * 3_600_000, '5h'],
  [47 * 3_600_000, '47h'], [48 * 3_600_000, '2d'], [5 * 86_400_000, '5d']])(
  'says an age of %i ms as "%s"', (age, label) => {
    expect(ageLabel(age)).toBe(label);
  },
);

it.each([[20_000, 'under a minute'], [60_000, '1 minute'], [20 * 60_000, '20 minutes'], [59 * 60_000, '59 minutes'],
  [3_600_000, '1h'], [125 * 60_000, '2h'], [47 * 3_600_000, '47h'], [48 * 3_600_000, '2d']])(
  'says %i ms elapsed as "%s", to the minute within the hour', (elapsed, label) => {
    expect(elapsedLabel(elapsed)).toBe(label);
  },
);
