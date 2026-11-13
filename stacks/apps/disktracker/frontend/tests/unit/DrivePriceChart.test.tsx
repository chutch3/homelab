import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { useState } from 'react';
import type { Offer, Observation, PriceRange } from '../../src/api';
import { DrivePriceChart } from '../../src/DrivePriceChart';
import type { Period } from '../../src/listing-query';
import { checkedAt, makeDrive, makeOffer } from '../fixtures/listings';

afterEach(cleanup);

const DAY = 86_400_000;
const range = (today: number | null, low: number, high: number, average: number, days: number): PriceRange => ({ today, low, high, average, days });
const ago = (days: number) => new Date(checkedAt.getTime() - days * DAY).toISOString();
const day = (days: number) => new Date(ago(days)).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
const price = (id: string, daysAgo: number, item: number, fields: Partial<Observation> = {}): Observation =>
  ({ ...makeOffer(id).latest, id, observed_at: ago(daysAgo), entered_at: ago(daysAgo), item_price_cents: item, total_cents: item, ...fields });
const drive = makeDrive('ST18000NM000J');
const offer = (id: string, store: string, prices: Observation[], lastCheckedDaysAgo = 0): Offer => makeOffer(id,
  { drive, mpn: drive.mpn, store, seller: '', observations: prices, last_checked_at: ago(lastCheckedDaysAgo) }, prices[prices.length - 1]);
// The lowest at either store: $190 for 50 days, $170 for 30, $180 for the last 10, as the server ranges it.
const BOTH_90 = range(18000, 17000, 19000, 18222, 90);
const spd = offer('spd', 'serverpartdeals', [price('spd-1', 60, 20000), price('spd-2', 20, 18000)]);
const ghd = offer('ghd', 'goharddrive', [price('ghd-1', 100, 19000), price('ghd-2', 40, 17000), price('ghd-3', 10, 18500)]);

/** The range the server gives for each period: the chart shows it, and draws the prices. */
type Ranges = Partial<Record<Period, PriceRange | null>>;

/** The chart as the drive's panel holds it: the period chosen is the panel's, and so is the range for it. */
function Panel({ listings, ranges, opensOn }: { listings: Offer[]; ranges: Ranges; opensOn: Period }) {
  const [days, setDays] = useState<Period>(opensOn);
  return <DrivePriceChart listings={listings} now={checkedAt} quietDays={7} days={days} range={ranges[days] ?? null} onDays={setDays} />;
}

function show(listings: Offer[], ranges: Ranges, days: Period = 90) {
  const { container } = render(<MantineProvider env="test"><Panel listings={listings} ranges={ranges} opensOn={days} /></MantineProvider>);
  const lines = () => [...container.querySelectorAll('.recharts-line-curve')].filter(line => line.getAttribute('d'));
  const ticks = (axis: 'xAxis' | 'yAxis') => [...container.querySelectorAll(`.recharts-${axis}-tick-labels text`)].map(tick => tick.textContent);
  const trend = within(screen.getByRole('region', { name: 'Price trend' }));
  /** The figures the trend opens with, each as its name, its amount and the few words under it. */
  const figures = () => trend.getAllByRole('term').map((term, index) => [term.textContent, trend.getAllByRole('definition')[index].textContent]);
  return { container, lines, ticks, trend, figures };
}

describe('DrivePriceChart', () => {
  it('opens with three figures to scan (today, the low and the average), then draws the lowest item price at any store as one stepped line with its average ruled across', async () => {
    const { container, lines, ticks, trend, figures } = show([spd, ghd], { 90: BOTH_90 });
    expect(figures()).toEqual([['Today', '$180.00' + '$10.00 above low'], ['Low', '$170.00' + `GoHardDrive, ${day(40)}`], ['Average', '$182.22' + 'over 90 days']]);
    // The chart pictures the range; no second picture or sentence repeats it.
    expect(trend.queryByRole('img')).not.toBeInTheDocument();
    expect(trend.queryByText(/^Low \$/)).not.toBeInTheDocument();
    await waitFor(() => expect(lines()).toHaveLength(1));
    // Stepped: each stretch of the line runs straight across or straight up or down, never on a slope between two prices.
    const points = lines()[0].getAttribute('d')!.split(/[ML]/).filter(Boolean).map(point => point.split(',').map(Number));
    expect(points.length).toBeGreaterThan(4);
    expect(points.slice(1).every(([x, y], index) => x === points[index][0] || y === points[index][1])).toBe(true);
    expect(container.querySelectorAll('.recharts-reference-line')).toHaveLength(1);
    // The price axis frames the prices rather than starting at zero; the days run from the period's first to today.
    // Its steps are whole tens of dollars, so the axis leaves the cents off.
    expect(ticks('yAxis')).toEqual(['$160', '$170', '$180', '$190', '$200']);
    expect(ticks('xAxis')).toEqual(['90d ago', '60', '30', 'Today']);
  });

  it("sets one store's own price against the lowest when it is chosen, cheapest store first", async () => {
    const { lines, trend } = show([ghd, spd], { 90: BOTH_90 });
    const compare = trend.getByRole('combobox', { name: 'Compare a store' });
    expect(within(compare).getAllByRole('option').map(option => option.textContent)).toEqual(['No store', 'ServerPartDeals, $180.00', 'GoHardDrive, $185.00']);
    await userEvent.selectOptions(compare, 'GoHardDrive, $185.00');
    await waitFor(() => expect(lines()).toHaveLength(2));
    expect(trend.getByText('GoHardDrive')).toBeVisible();
    expect(trend.getByText('Lowest at any store')).toBeVisible();
    await userEvent.selectOptions(compare, 'No store');
    await waitFor(() => expect(lines()).toHaveLength(1));
  });

  it('looks back over the period it opens on, and over another when one is chosen', async () => {
    const { ticks, trend, figures } = show([spd, ghd], { 180: range(18000, 17000, 19000, 18300, 100), 30: range(18000, 17000, 18500, 17333, 30) }, 180);
    expect(trend.getByRole('button', { name: '180 days' })).toHaveAttribute('aria-pressed', 'true');
    // Short to look at, whole to a screen reader.
    expect(trend.getByRole('button', { name: '180 days' })).toHaveTextContent(/^180d$/);
    // Prices only go back 100 days.
    expect(figures()).toEqual([['Today', '$180.00' + '$10.00 above low'], ['Low', '$170.00' + `GoHardDrive, ${day(40)}`], ['Average', '$183.00' + 'only 100 days']]);
    await userEvent.click(trend.getByRole('button', { name: '30 days' }));
    expect(trend.getByRole('button', { name: '30 days' })).toHaveAttribute('aria-pressed', 'true');
    expect(trend.getByRole('button', { name: '180 days' })).toHaveAttribute('aria-pressed', 'false');
    expect(figures()).toEqual([['Today', '$180.00' + '$10.00 above low'], ['Low', '$170.00' + `GoHardDrive, ${day(40)}`], ['Average', '$173.33' + 'over 30 days']]);
    await waitFor(() => expect(ticks('xAxis')).toEqual(['30d ago', '20', '10', 'Today']));
  });

  it('ends the line on a price recorded this instant, straight down from the one it replaced', async () => {
    const { lines, figures } = show([offer('a', 'serverpartdeals', [price('a-1', 10, 20000), price('a-2', 0, 18000)])], { 90: range(18000, 18000, 20000, 20000, 10) });
    expect(figures()[0]).toEqual(['Today', '$180.00' + 'At its lowest']);
    await waitFor(() => expect(lines()).toHaveLength(1));
    const points = lines()[0].getAttribute('d')!.split(/[ML]/).filter(Boolean).map(point => point.split(',').map(Number));
    const [before, last] = points.slice(-2);
    expect(last[0]).toBe(before[0]);
    // Lower on the page is a higher y: the line drops to the cheaper price.
    expect(last[1]).toBeGreaterThan(before[1]);
  });

  it('offers no store to compare when only one sells the drive', () => {
    const { trend } = show([spd], { 90: range(18000, 18000, 20000, 19333, 60) });
    expect(trend.queryByRole('combobox', { name: 'Compare a store' })).not.toBeInTheDocument();
  });

  it('says a drive is at its low, that its price has not changed, or that it is new', () => {
    expect(show([offer('a', 'serverpartdeals', [price('a-1', 60, 20000), price('a-2', 20, 18000)])], { 90: range(18000, 18000, 20000, 19333, 60) }).figures()[0]).toEqual(['Today', '$180.00' + 'At its lowest']);
    cleanup();
    // One price all along is one figure: its low and its average would only say it again.
    expect(show([offer('a', 'serverpartdeals', [price('a-1', 200, 20000)])], { 90: range(20000, 20000, 20000, 20000, 90) }).figures()).toEqual([['Today', '$200.00' + 'No change in 90 days']]);
    cleanup();
    expect(show([offer('a', 'serverpartdeals', [price('a-1', 12, 20000)])], { 90: range(20000, 20000, 20000, 20000, 12) }).figures()).toEqual([['Today', '$200.00' + 'Tracked for 12 days']]);
  });

  it('says when no store has the drive in stock, while still showing what it cost', () => {
    const soldOut = offer('a', 'serverpartdeals', [price('a-1', 30, 20000), price('a-2', 20, 18000), price('a-3', 5, 18000, { in_stock: false })]);
    const { figures } = show([soldOut], { 90: range(null, 18000, 20000, 18800, 30) });
    expect(figures()).toEqual([['Today', '—' + 'Not in stock'], ['Low', '$180.00' + `ServerPartDeals, ${day(20)}`], ['Average', '$188.00' + 'only 30 days']]);
  });

  it('says so instead of drawing a chart when there is nothing to draw', () => {
    const never = offer('a', 'serverpartdeals', [price('a-1', 20, 20000, { in_stock: false })]);
    const { container, trend } = show([never], { 90: null });
    expect(trend.getByText('No prices in the last 90 days')).toBeVisible();
    expect(container.querySelector('.recharts-surface')).not.toBeInTheDocument();
    cleanup();
    const today = show([offer('b', 'serverpartdeals', [price('b-1', 0, 20000)])], { 90: range(20000, 20000, 20000, 20000, 0) });
    expect(today.figures()).toEqual([['Today', '$200.00' + 'First seen today']]);
    expect(today.container.querySelector('.recharts-surface')).not.toBeInTheDocument();
  });
});
