import { describe, expect, it } from 'vitest';
import { dailyPoints } from '../../src/price-chart-points';
import { historyPrices } from '../fixtures/listings';

const dayOf = (value: string) => { const at = new Date(value); return new Date(at.getFullYear(), at.getMonth(), at.getDate()).getTime(); };
const at = (id: string, observed: string, total: number) => ({ ...historyPrices[0], id, observed_at: observed, entered_at: observed, total_cents: total });

describe('chart points for price history', () => {
  it('gives one point per day a price was recorded, at the start of that day, oldest first', () => {
    const [previous, current] = historyPrices;
    expect(dailyPoints([current, previous])).toEqual([
      { id: 'previous', x: dayOf('2026-09-14T12:00:00Z'), y: 23000 },
      { id: 'current', x: dayOf('2026-09-18T12:00:00Z'), y: 21500 },
    ]);
  });

  it('shows a day checked more than once at the price it ended on', () => {
    const prices = [at('noon', '2026-09-14T12:00:00Z', 59000), at('morning', '2026-09-14T10:00:00Z', 60000), at('later', '2026-09-18T12:00:00Z', 57900)];
    expect(dailyPoints(prices)).toEqual([
      { id: 'noon', x: dayOf('2026-09-14T12:00:00Z'), y: 59000 },
      { id: 'later', x: dayOf('2026-09-18T12:00:00Z'), y: 57900 },
    ]);
  });

  it('returns an empty series when there are no observations', () => {
    expect(dailyPoints([])).toEqual([]);
  });
});
