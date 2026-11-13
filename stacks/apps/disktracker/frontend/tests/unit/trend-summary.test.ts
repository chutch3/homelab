import { describe, expect, it } from 'vitest';
import type { TrendSeries } from '../../src/api';
import { movedLabel, summaryOf } from '../../src/trend-summary';

const series = (...points: [number, number][]): TrendSeries =>
  ({ counted: 3, of: 3, points: points.map(([days_ago, median]) => ({ days_ago, median, low: median - 100, high: median + 100 })) });

describe('a trend in summary', () => {
  it('is where it stands today, where it stood as its points begin, and the average of its days', () => {
    expect(summaryOf(series([3, 2000], [2, 2000], [1, 1700], [0, 1600]))).toEqual({ today: 1600, start: 2000, since: 3, average: 1825, low: 1500, high: 1700 });
  });

  it('is absent when no day could be priced, or when the last day priced is not today', () => {
    expect(summaryOf(series())).toBeNull();
    expect(summaryOf(series([5, 2000], [4, 2000]))).toBeNull();
  });
});

describe('how a trend has moved', () => {
  it.each([
    [2000, 1600, true, { down: true, text: '20.0% in 90d' }],
    [1600, 2000, true, { down: false, text: '25.0% in 90d' }],
    [-909, -609, false, { down: false, text: '3.0 pts in 90d' }],
    [300, -150, false, { down: true, text: '4.5 pts in 90d' }],
  ])('from %i to %i is said as a share of where it began, or in points when it is already a percentage', (from, to, relative, said) => {
    expect(movedLabel(from, to, 90, relative)).toEqual(said);
  });

  it('says so when it has not moved', () => {
    expect(movedLabel(2000, 2000, 30, true)).toEqual({ down: null, text: 'No change, 30d' });
    expect(movedLabel(100, 100, 30, false)).toEqual({ down: null, text: 'No change, 30d' });
  });
});
