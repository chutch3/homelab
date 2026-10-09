import { describe, expect, it } from 'vitest';
import { lowestObserved } from '../../src/lowest-observed';
import { makeListing } from '../fixtures/listings';

const price = (id: string, observed_at: string, total_cents: number, in_stock = true) =>
  ({ ...makeListing(id).latest, id, observed_at, total_cents, in_stock });

describe('the lowest observed price across a drive’s offers', () => {
  it('is the cheapest in-stock total, counted over every in-stock price and the dates they span', () => {
    const a = makeListing('a', { observations: [price('a1', '2026-09-10T12:00:00Z', 20000), price('a2', '2026-09-12T12:00:00Z', 18000)] });
    const b = makeListing('b', { observations: [price('b1', '2026-09-08T12:00:00Z', 19000), price('b2', '2026-09-15T12:00:00Z', 9000, false)] });
    expect(lowestObserved([a, b])).toEqual({
      listing: a, observation: a.observations[1], count: 3, from: '2026-09-08T12:00:00Z', to: '2026-09-12T12:00:00Z',
    });
  });

  it('prefers the most recent time a tied low was seen', () => {
    const a = makeListing('a', { observations: [price('early', '2026-09-10T12:00:00Z', 18000), price('late', '2026-09-14T12:00:00Z', 18000)] });
    expect(lowestObserved([a])?.observation.id).toBe('late');
  });

  it('is absent when nothing was ever in stock', () => {
    expect(lowestObserved([makeListing('a', { observations: [price('gone', '2026-09-10T12:00:00Z', 9000, false)] })])).toBeNull();
    expect(lowestObserved([])).toBeNull();
  });
});
