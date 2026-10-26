import { useState } from 'react';
import { LineChart } from '@mantine/charts';
import { Button, Group, NativeSelect, Text } from '@mantine/core';
import type { Offer, PriceRange } from './api';
import { dollars, sellerLabel } from './listing-display';
import { periods, type Period } from './listing-query';
import { priceSeries, type PriceStep } from './price-range';

const DAY = 86_400_000;
/** Cents between the price axis's round ends: $10. */
const AXIS_STEP = 1000;
const dateLabel = (moment: number) => new Date(moment).toLocaleDateString();
/** A day in a few characters, for under a figure: the year is the chart's to say. */
const dayLabel = (moment: number) => new Date(moment).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
const daysLabel = (days: number) => days === 1 ? '1 day' : `${days} days`;

type Props = {
  /** One drive's offers in one condition, each with every price it has had. */
  listings: Offer[]; now: Date;
  /** An offer unchecked for longer than this many days is taken to have ended at its last check. */
  quietDays: number;
  /** The period shown, and the way to choose another: the panel holding the chart owns it. */
  days: Period; onDays: (days: Period) => void;
  /** Where the lowest price has been over the period, as the server works it out; null when nothing was in stock. */
  range: PriceRange | null;
};

/** How today's price stands against the period, in a few words to sit under it. */
function standing(range: PriceRange, days: Period): string {
  if (range.today === null) return 'Not in stock';
  if (range.high === range.low) return range.days >= days ? `No change in ${days} days` : range.days ? `Tracked for ${daysLabel(range.days)}` : 'First seen today';
  return range.today === range.low ? 'At its lowest' : `${dollars(range.today - range.low)} above low`;
}

/** The price a stepped line shows at a moment: the step then in force, or the last one ending there
 * (its closing point, or a price recorded that instant), or nothing in a gap. */
const priceAt = (steps: PriceStep[], moment: number) =>
  (steps.find(step => step.from <= moment && moment < step.to) ?? [...steps].reverse().find(step => step.to === moment))?.price ?? null;
/** The moments a stepped line needs a point at: where each step starts and ends, and just after an
 * end nothing follows, so the line stops there instead of running on to the next step. */
const turns = (steps: PriceStep[]) => steps.flatMap((step, index) => [step.from, step.to, ...(steps[index + 1]?.from === step.to ? [] : [step.to + 1])]);

/** A drive's item price in one condition over a period: how today stands against the period's
 * low and average as three figures to scan, then one stepped line of the lowest price at any store with its average ruled across.
 * One store's own price is drawn against it when that store is chosen. */
export function DrivePriceChart({ listings, now, quietDays, days, onDays, range }: Props) {
  const [compared, setCompared] = useState('');
  const series = priceSeries(listings, now, days, quietDays);
  // Cheapest today first; a store with nothing on sale now comes last.
  const stores = [...series.offers].sort((a, b) => (a.today ?? Infinity) - (b.today ?? Infinity));
  const store = stores.find(offer => offer.listing.id === compared);
  const low = range && [...series.lowest].reverse().find(step => step.price === range.low);
  const lines = [series.lowest, ...(store ? [store.steps] : [])];
  const moments = [...new Set(lines.flatMap(turns))].sort((a, b) => a - b);
  const rows = moments.map(moment => ({ moment, lowest: priceAt(series.lowest, moment), ...(store && { store: priceAt(store.steps, moment) }) }));
  // The axis frames the prices rather than starting at zero, so a change of a few dollars shows.
  const prices = lines.flat().map(step => step.price), lowest = Math.min(...prices), highest = Math.max(...prices);
  const room = Math.max((highest - lowest) * 0.2, AXIS_STEP);
  const step = Math.max(AXIS_STEP, Math.ceil((highest - lowest + 2 * room) / 4 / AXIS_STEP) * AXIS_STEP);
  const priceTicks = [Math.max(0, Math.floor((lowest - room) / step) * step)];
  while (priceTicks[priceTicks.length - 1] < highest + room) priceTicks.push(priceTicks[priceTicks.length - 1] + step);
  const dayTicks = [0, 1, 2, 3].map(third => series.start + third * days * DAY / 3);
  return <section aria-label="Price trend" className="price-trend">
    <Group justify="space-between" align="end" mb="xs">
      <h3>Price trend</h3>
      <Group gap={0} role="group" aria-label="Period" className="segmented">{periods.map(period =>
        <Button key={period} size="xs" variant={period === days ? 'filled' : 'default'} aria-pressed={period === days} aria-label={`${period} days`} onClick={() => onDays(period)}>{period}d</Button>)}
      </Group>
    </Group>
    {!range ? <Text size="sm" c="dimmed">No prices in the last {days} days</Text> : <>
      <dl className="trend-stats">
        <div><dt>Today</dt><dd><strong>{range.today === null ? '—' : dollars(range.today)}</strong><span>{standing(range, days)}</span></dd></div>
        {/* One price all along is one figure: its low and its average would only say it again. */}
        {low && range.high !== range.low && <>
          <div><dt>Low</dt><dd><strong>{dollars(range.low)}</strong><span>{`${sellerLabel(low.listing)}, ${dayLabel(low.since)}`}</span></dd></div>
          <div><dt>Average</dt><dd><strong>{dollars(range.average)}</strong><span>{`${range.days < days ? 'only' : 'over'} ${daysLabel(range.days)}`}</span></dd></div>
        </>}
      </dl>
      {stores.length > 1 && <NativeSelect mt="sm" className="compare-store" label="Compare a store" aria-label="Compare a store" value={store ? compared : ''} onChange={event => setCompared(event.currentTarget.value)}
        data={[{ value: '', label: 'No store' }, ...stores.map(({ listing, today }) => ({ value: listing.id, label: `${sellerLabel(listing)}, ${today === null ? 'not on sale' : dollars(today)}` }))]} />}
      {/* The chart is the board's green with the lowest price in white across it. */}
      {range.days > 0 && <div className="history"><LineChart
        h={240}
        data={rows}
        dataKey="moment"
        series={[{ name: 'lowest', label: 'Lowest at any store', color: '#0e5a47' }, ...(store ? [{ name: 'store', label: sellerLabel(store.listing), color: '#c9982b' }] : [])]}
        textColor="#4c5753" gridColor="#dde1df"
        // A price holds until the day it is seen to change: across, then straight to the next.
        curveType="stepAfter" strokeWidth={3} withDots={false} connectNulls={false}
        withLegend={Boolean(store)}
        gridAxis="y"
        strokeDasharray="1 0"
        referenceLines={[{ y: range.average, label: 'Average', color: '#4c5753' }]}
        xAxisProps={{ type: 'number', domain: [series.start, series.end], ticks: dayTicks,
          tickFormatter: (moment: number) => moment === series.end ? 'Today' : moment === series.start ? `${days}d ago` : String(Math.round((series.end - moment) / DAY)) }}
        // The axis steps in whole tens of dollars, so it leaves the cents off.
        yAxisProps={{ domain: [priceTicks[0], priceTicks[priceTicks.length - 1]], ticks: priceTicks, tickFormatter: (value: number) => `$${value / 100}` }}
        valueFormatter={(value: number) => dollars(value)}
        tooltipProps={{ labelFormatter: moment => typeof moment === 'number' ? dateLabel(moment) : moment }}
      /></div>}
    </>}
  </section>;
}
