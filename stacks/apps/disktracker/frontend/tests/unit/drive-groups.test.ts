import { describe, expect, it } from 'vitest';
import { knownDrives } from '../../src/drive-groups';
import { makeDrive, makeOffer } from '../fixtures/listings';

describe('drives already known', () => {
  it('are each drive once, by MPN, named by a listing title', () => {
    const exos = makeDrive('ST18000NM000J');
    const listings = [
      makeOffer('Exos X18 at store B', { drive: exos }), makeOffer('Exos X18', { drive: exos }),
      makeOffer('Red', { drive: makeDrive('WD120EFBX') }),
    ];
    expect(knownDrives(listings)).toEqual([
      { mpn: 'ST18000NM000J', title: 'Exos X18 at store B' }, { mpn: 'WD120EFBX', title: 'Red' },
    ]);
  });
});
