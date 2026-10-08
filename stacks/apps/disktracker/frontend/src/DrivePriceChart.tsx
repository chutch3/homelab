import { LineChart } from '@mantine/charts';
import { Text } from '@mantine/core';
import type { Listing } from './api';
import { dollars, sellerLabel } from './listing-display';
import { driveChartSeries } from './drive-chart-series';
import { lowestObserved } from './lowest-observed';

const dateLabel = (value: number | string) => new Date(value).toLocaleDateString();
const DAY = 86_400_000;
/** The most days the axis names; more are thinned evenly, keeping the first and the last. */
const MAX_TICKS = 6;
/** Cents between the price axis's round ends: $10. */
const AXIS_STEP = 1000;

type Props = { listings: Listing[] };
type DotProps = { cx?: number; cy?: number; value?: number | null; stroke?: string; index?: number };

/** The price by day of each offer given, which share a condition: a dot for a day it was checked, joined into a line where it has
 * more than one day. A day checked more than once shows the price it ended on. */
export function DrivePriceChart({ listings }: Props) {
  const series = driveChartSeries(listings);
  const low = lowestObserved(listings);
  const span = low && (dateLabel(low.from) === dateLabel(low.to) ? dateLabel(low.from) : `${dateLabel(low.from)} to ${dateLabel(low.to)}`);
  const days = [...new Set(series.flatMap(s => s.points.map(point => point.x)))].sort((a, b) => a - b);
  // One row per day, holding each offer's price that day under its id.
  const rows = days.map(day => ({ day, ...Object.fromEntries(series.flatMap(s => s.points.filter(point => point.x === day).map(point => [s.listingId, point.y]))) }));
  const every = Math.max(1, Math.ceil((days.length - 1) / (MAX_TICKS - 1)));
  const ticks = days.filter((_, index) => index % every === 0 || index === days.length - 1);
  const prices = series.flatMap(s => s.points.map(point => point.y));
  // The axis frames the prices rather than starting at zero, so a change of a few dollars shows.
  const lowest = Math.min(...prices), highest = Math.max(...prices), room = Math.max((highest - lowest) * 0.2, AXIS_STEP);
  // About four even steps of whole tens of dollars, from just under the lowest price to just over the highest.
  const step = Math.max(AXIS_STEP, Math.ceil((highest - lowest + 2 * room) / 4 / AXIS_STEP) * AXIS_STEP);
  const priceTicks = [Math.max(0, Math.floor((lowest - room) / step) * step)];
  while (priceTicks[priceTicks.length - 1] < highest + room) priceTicks.push(priceTicks[priceTicks.length - 1] + step);
  return <section aria-label="Price trend">
    <h3>Price trend</h3>
    {low && <div className="lowest-observed">
      <Text size="sm">Lowest price {dollars(low.observation.total_cents)} · {sellerLabel(low.listing)} · {dateLabel(low.observation.observed_at)}</Text>
      <Text size="xs" c="dimmed">From {low.count} in-stock price{low.count === 1 ? '' : 's'}, {span}</Text>
    </div>}
    {series.length === 0 && <Text size="sm" c="dimmed">No price history yet</Text>}
    <LineChart
      h={240}
      data={rows}
      dataKey="day"
      series={series.map(s => ({ name: s.listingId, label: s.label, color: s.color }))}
      curveType="linear" strokeWidth={2} connectNulls
      withLegend={series.length > 1}
      gridAxis="x"
      strokeDasharray="1 0"
      // Half a day either side, so a single day's dots sit in the middle rather than on the axis.
      xAxisProps={{ type: 'number', domain: days.length ? [days[0] - DAY / 2, days[days.length - 1] + DAY / 2] : [0, 1], ticks, tickFormatter: dateLabel }}
      yAxisProps={{ ...(prices.length && { domain: [priceTicks[0], priceTicks[priceTicks.length - 1]], ticks: priceTicks }), tickFormatter: (value: number) => dollars(value) }}
      valueFormatter={(value: number) => dollars(value)}
      tooltipProps={{ labelFormatter: day => typeof day === 'number' ? dateLabel(day) : day }}
      lineProps={{
        dot: ({ cx, cy, value, stroke, index }: DotProps) => value == null || cx == null || cy == null ? <g key={index} />
          : <circle key={index} data-testid="price-chart-point" cx={cx} cy={cy} r={5} fill={stroke} stroke="var(--mantine-color-body)" strokeWidth={2} />,
      }}
    />
  </section>;
}
