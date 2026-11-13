import { dollars } from './listing-display';
import type { PriceRange } from './api';

/** The picture's full width, as a percentage above the drive's lowest price. Every row shares it, so
 * a short line is a price that has barely moved. */
const SCALE = 30;

type Props = { range: PriceRange; /** The period asked for; the range may cover fewer days. */ days: number };

/** How far above its lowest price a drive has been over a period: a line from that low out to its
 * highest, a tick at its average and a dot at today, with the same in a few words beside it. A drive
 * with fewer days of prices than the period is marked, and one whose price has not moved is words alone. */
export function PriceRangeBar({ range, days }: Props) {
  const { today, low, high, average } = range;
  if (today === null) return null;
  const span = range.days === 1 ? '1 day' : `${range.days} days`;
  if (high === low) return <span className="range-label">{range.days >= days ? 'No change' : range.days ? `Tracked for ${span}` : 'First seen today'}</span>;
  const above = (price: number) => (price / low - 1) * 100;
  const along = (price: number) => `${Math.min(100, above(price) / SCALE * 100).toFixed(1)}%`;
  const short = range.days < days;
  // In words first; the picture says the same for whoever reads it at a glance.
  return <>
    <span className="range-label">{today === low ? 'At its lowest' : `+${above(today).toFixed(1)}% above its low`}{short && `, tracked ${span}`}</span>
    <div role="img" className={short ? 'range-bar short' : 'range-bar'}
      aria-label={`Today ${dollars(today)}, ${above(today).toFixed(1)}% above the lowest. Over ${span}: lowest ${dollars(low)}, average ${dollars(average)}, highest ${dollars(high)}.`}>
      <span className={above(high) > SCALE ? 'range-span over' : 'range-span'} style={{ width: along(high) }} />
      <span className="range-average" style={{ left: along(average) }} />
      <span className="range-today" style={{ left: along(today) }} />
    </div>
  </>;
}
