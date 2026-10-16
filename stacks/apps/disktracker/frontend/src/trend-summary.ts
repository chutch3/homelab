import type { TrendSeries } from './api';

/** Where a trend stands: today's median with the middle half around it, where it stood as its
 * points begin and how many days ago that was, and the average of its days. */
export type TrendSummary = { today: number; start: number; since: number; average: number; low: number; high: number };

/** Null when there is nothing to say of today: no day could be priced, or the last that could was earlier. */
export function summaryOf({ points }: TrendSeries): TrendSummary | null {
  const last = points[points.length - 1];
  if (!last || last.days_ago !== 0) return null;
  return {
    today: last.median, low: last.low, high: last.high, start: points[0].median, since: points[0].days_ago,
    average: Math.round(points.reduce((sum, point) => sum + point.median, 0) / points.length),
  };
}

/** How far a trend has moved over its days, and which way: as a share of where it began, or in
 * points when its values are already hundredths of a percent. down is null when it has not moved. */
export function movedLabel(from: number, to: number, days: number, relative: boolean): { down: boolean | null; text: string } {
  const by = relative ? (to / from - 1) * 100 : (to - from) / 100;
  if (Math.abs(by) < 0.05) return { down: null, text: `No change, ${days}d` };
  return { down: by < 0, text: `${Math.abs(by).toFixed(1)}${relative ? '%' : ' pts'} in ${days}d` };
}
