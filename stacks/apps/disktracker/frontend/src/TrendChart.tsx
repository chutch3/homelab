import { LineChart } from '@mantine/charts';
import type { TrendSeries } from './api';

type Props = {
  series: TrendSeries;
  /** The days the chart runs across, whatever days its points cover. */
  days: number;
  /** The ends of the value axis, so charts shown together share a scale. */
  domain: [number, number];
  /** Whether to draw the middle half either side of the median: not when too few drives make it one. */
  band: boolean;
  format: (value: number) => string;
  /** A value ruled across the chart: an average, or the zero a store is measured from. */
  rule?: number;
  height?: number;
};

/** A trend as a stepped line of each day's median, with the middle half as a fainter line above and
 * below it. A value holds until the day it changes. */
export function TrendChart({ series, days, domain, band, format, rule, height = 200 }: Props) {
  const strong = '#0e5a47', faint = '#a8cdbf', text = '#4c5753';
  return <LineChart
    h={height}
    // Days ago run right to left, so the axis counts up to today at zero.
    data={series.points.map(point => ({ day: -point.days_ago, median: point.median, ...(band && { low: point.low, high: point.high }) }))}
    dataKey="day"
    series={[...(band ? [{ name: 'high', label: 'Middle half, upper', color: faint }, { name: 'low', label: 'Middle half, lower', color: faint }] : []),
      { name: 'median', label: 'Median', color: strong }]}
    curveType="stepAfter" strokeWidth={2} withDots={false} connectNulls={false}
    gridAxis="y" strokeDasharray="1 0" textColor={text} gridColor="#dde1df"
    referenceLines={rule === undefined ? [] : [{ y: rule, color: text }]}
    // Thirds of the period, each a whole day: a fortnight's are not.
    xAxisProps={{ type: 'number', domain: [-days, 0], ticks: [0, 1, 2, 3].map(third => -days + Math.round(third * days / 3)),
      tickFormatter: (day: number) => day === 0 ? 'Today' : day === -days ? `${days}d ago` : String(-day) }}
    yAxisProps={{ domain, ticks: [domain[0], (domain[0] + domain[1]) / 2, domain[1]], tickFormatter: format }}
    valueFormatter={format}
    tooltipProps={{ labelFormatter: day => typeof day === 'number' ? (day === 0 ? 'Today' : `${-day} days ago`) : day }}
  />;
}
