import type { Listing } from './api';
import { dailyPoints, type ChartPoint } from './price-chart-points';
import { sellerLabel } from './listing-display';

export type DriveSeries = { listingId: string; label: string; color: string; points: ChartPoint[] };

// Validated for all-pairs (scatter) use: node scripts/validate_palette.js "<these>" --mode light --pairs all
const CATEGORICAL_COLORS = ['#2a78d6', '#eb6834', '#1baf7a'];
const OTHER_COLOR = '#8a8a86';

/** One series per offer, named by its store: the offers charted together share a condition, so
 * the store is what tells them apart. */
export function driveChartSeries(listings: Listing[]): DriveSeries[] {
  return [...listings]
    .sort((a, b) => a.id.localeCompare(b.id))
    .map((listing, index) => ({
      listingId: listing.id, label: sellerLabel(listing),
      color: CATEGORICAL_COLORS[index] ?? OTHER_COLOR,
      points: dailyPoints(listing.observations),
    }))
    .filter(series => series.points.length > 0);
}
