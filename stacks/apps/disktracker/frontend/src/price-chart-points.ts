import type { Observation } from './api';
import { compareObservations } from './price-change';

export type ChartPoint = { id: string; x: number; y: number };

/** The start of the local day a moment falls in, in milliseconds. */
function dayStart(moment: string): number {
  const at = new Date(moment);
  return new Date(at.getFullYear(), at.getMonth(), at.getDate()).getTime();
}

/** One point per day a price was recorded, oldest first: a day checked more than once shows the
 * price it ended on, so repeated checks do not pile up as points on the same date. */
export function dailyPoints(observations: Observation[]): ChartPoint[] {
  const byDay = new Map<number, ChartPoint>();
  for (const observation of [...observations].sort(compareObservations)) {
    const x = dayStart(observation.observed_at);
    byDay.set(x, { id: observation.id, x, y: observation.total_cents });
  }
  return [...byDay.values()].sort((a, b) => a.x - b.x);
}
