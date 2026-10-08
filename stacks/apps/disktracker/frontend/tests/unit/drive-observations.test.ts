import { describe, expect, it } from 'vitest';
import { combinedObservations } from '../../src/drive-observations';
import { makeDrive, makeListing } from '../fixtures/listings';

describe('combining observations across every listing sharing a drive', () => {
  it('pairs each observation with its own listing, ordered chronologically regardless of listing order', () => {
    const drive = makeDrive('ST18000NM003D');
    const earlier = makeListing('a', { drive, seller: 'ServerPartDeals' }, { observed_at: '2026-09-20T12:00:00Z', entered_at: '2026-09-20T12:00:00Z' });
    const later = makeListing('b', { drive, seller: 'eBay - drivedeals' }, { observed_at: '2026-09-21T12:00:00Z', entered_at: '2026-09-21T12:00:00Z' });
    const rows = combinedObservations([later, earlier]);
    expect(rows.map(row => row.listing.seller)).toEqual(['ServerPartDeals', 'eBay - drivedeals']);
    expect(rows.map(row => row.observation.id)).toEqual([earlier.latest.id, later.latest.id]);
  });

  it('includes every observation from a listing with more than one', () => {
    const drive = makeDrive('ST18000NM003D');
    const listing = makeListing('a', { drive, seller: 'ServerPartDeals', observations: [
      { ...makeListing('a').latest, id: 'first', observed_at: '2026-09-19T12:00:00Z', entered_at: '2026-09-19T12:00:00Z' },
      { ...makeListing('a').latest, id: 'second', observed_at: '2026-09-20T12:00:00Z', entered_at: '2026-09-20T12:00:00Z' },
    ] });
    const rows = combinedObservations([listing]);
    expect(rows.map(row => row.observation.id)).toEqual(['first', 'second']);
  });
});
