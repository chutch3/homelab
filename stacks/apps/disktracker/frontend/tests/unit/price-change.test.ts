import { describe, expect, it } from 'vitest';
import { priceChange } from '../../src/price-change';
import { historyPrices } from '../fixtures/listings';

const [previous, current] = historyPrices;

describe('price change between adjacent observations', () => {
  it('compares totals in cents', () => {
    expect(priceChange(historyPrices)).toMatchObject({ previous, current, difference: -1500, percentage: -6.5, reason: null });
  });
  it('orders by observation time, then entry time and ID, without changing the input', () => {
    const backdated = { ...previous, id: 'backdated', observed_at: '2026-09-01T12:00:00Z', entered_at: '2026-09-22T12:00:00Z' };
    const sameTime = { ...current, id: 'later-entry', entered_at: '2026-09-19T12:00:00Z', total_cents: 21000 };
    const rows = [sameTime, backdated, current, previous];
    expect(priceChange(rows)).toMatchObject({ previous: current, current: sameTime, difference: -500 });
    expect(rows).toEqual([sameTime, backdated, current, previous]);
    const sameEntry = { ...sameTime, id: 'z-last', total_cents: 20500 };
    expect(priceChange([sameEntry, sameTime]).current).toEqual(sameEntry);
  });
  it.each([[[]], [[current]]])('does not invent a change with fewer than two observations', rows => {
    expect(priceChange(rows)).toMatchObject({ difference: null, percentage: null, reason: 'insufficient' });
  });
  it('shows an absolute change from zero but no percentage, and distinguishes unchanged prices', () => {
    const zero = { ...previous, total_cents: 0 };
    expect(priceChange([zero, current])).toMatchObject({ difference: 21500, percentage: null, reason: null });
    expect(priceChange([previous, { ...current, total_cents: previous.total_cents }])).toMatchObject({ difference: 0, percentage: 0, reason: null });
  });
  it('rounds increases and decreases symmetrically to one decimal place', () => {
    const baseline = { ...previous, total_cents: 2000 };
    expect(priceChange([baseline, { ...current, total_cents: 2001 }]).percentage).toBe(0.1);
    expect(priceChange([baseline, { ...current, total_cents: 1999 }]).percentage).toBe(-0.1);
  });
});
