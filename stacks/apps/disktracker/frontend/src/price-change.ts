import type { Observation } from './api';
import { dollars } from './listing-display';


type Reason = 'insufficient' | null;

type PriceChange = {
  history: Observation[]; previous: Observation | null; current: Observation | null;
  difference: number | null; percentage: number | null; reason: Reason;
};

export function compareObservations(a: Observation, b: Observation): number {
  return Date.parse(a.observed_at) - Date.parse(b.observed_at)
    || Date.parse(a.entered_at) - Date.parse(b.entered_at) || a.id.localeCompare(b.id);
}

export function priceChange(observations: Observation[]): PriceChange {
  const history = [...observations].sort(compareObservations);
  const previous = history.at(-2) ?? null, current = history.at(-1) ?? null;
  if (!previous || !current) return { history, previous, current, difference: null, percentage: null, reason: 'insufficient' };
  const before = previous.total_cents, difference = current.total_cents - before;
  // Integer cents keep the subtraction exact; round the percentage symmetrically.
  const percentage = before > 0 ? Math.sign(difference) * Math.round(Math.abs(difference) * 1000 / before) / 10 : null;
  return { history, previous, current, difference, percentage, reason: null };
}

export function amountText({ difference, percentage }: Pick<PriceChange, 'difference' | 'percentage'>): string | null {
  if (difference === null) return null;
  if (difference === 0) return 'No change';
  const percent = percentage === null ? '' : ` (${Math.abs(percentage).toFixed(1)}%)`;
  return `${difference < 0 ? '▼' : '▲'} ${dollars(Math.abs(difference))}${percent}`;
}
