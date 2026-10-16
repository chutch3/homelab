import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { DisktrackerApi, PriceMark, TrendPoint, TrendSeries, Trends, TrendSplit } from '../../src/api';
import { renderApp } from '../fixtures/render-app';
import { checkedAt } from '../fixtures/listings';

afterEach(() => { cleanup(); window.history.replaceState(null, '', '/'); });

const point = (days_ago: number, median: number, low = median, high = median): TrendPoint => ({ days_ago, median, low, high });
const series = (counted: number, of: number, ...points: TrendPoint[]): TrendSeries => ({ counted, of, points });
/** Three of four drives followed: $20 a terabyte until ten days ago, $16 since. */
const market = series(3, 4, point(90, 2000, 1500, 2500), point(11, 2000, 1500, 2500), point(10, 1600, 1300, 2300), point(0, 1600, 1300, 2300));
const parts: Record<TrendSplit, Trends['parts']> = {
  condition: [{ key: 'manufacturer_recertified', series: series(3, 3, point(90, 1200), point(0, 1100)) }],
  capacity: [
    { key: '10000', series: series(3, 4, point(90, 1250, 1000, 1500), point(0, 1000, 900, 1100)) },
    { key: '18000', series: series(1, 1, point(90, 2000), point(0, 2000)) },
    { key: '960', series: series(0, 2) },
  ],
  store: [
    { key: 'goharddrive', series: series(4, 9, point(90, 909, 500, 1200), point(0, 609, 300, 900)) },
    { key: 'serverpartdeals', series: series(2, 12, point(90, -300), point(0, -300)) },
    { key: 'westerndigital', series: series(0, 5) },
  ],
};
/** A drive in stock today as the server reports it, by its name, capacity and price per terabyte in cents. */
const mark = (title: string, capacity_gb: number, per_tb_cents: number, lowest = false): PriceMark =>
  ({ drive_id: title, condition: 'new', title, capacity_gb, per_tb_cents, lowest });
/** Prices going back far enough for every period. */
const longAgo = new Date(checkedAt.getTime() - 400 * 86_400_000).toISOString();
const answering = () => vi.fn<DisktrackerApi['trends']>(async (days, by) => ({ days, by, market, parts: by ? parts[by] : [], since: longAgo }));
const open = async (trends: DisktrackerApi['trends'], path = '/trends') => {
  window.history.replaceState(null, '', path);
  renderApp({ trends });
  return within(await screen.findByRole('region', { name: 'Typical item price per TB' }));
};

describe('Trends page', () => {
  it('is reached from the header, and says what a terabyte typically costs today and how that has moved', async () => {
    const user = userEvent.setup(), trends = answering();
    renderApp({ trends });
    await user.click(await screen.findByRole('link', { name: 'Trends' }));
    expect(window.location.pathname).toBe('/trends');
    expect(screen.getByRole('link', { name: 'Trends' })).toHaveAttribute('aria-current', 'page');
    expect(await screen.findByRole('heading', { level: 1, name: 'Trends' })).toBeVisible();
    const typical = within(await screen.findByRole('region', { name: 'Typical item price per TB' }));
    expect(typical.getByText('$16.00')).toBeVisible();
    // The arrow is for the eye; the word says the same to a screen reader.
    expect(typical.getByText(/20\.0% in 90d/)).toHaveTextContent('↓ Down 20.0% in 90d');
    expect(typical.getByText('Middle half $13.00 to $23.00')).toBeVisible();
    expect(typical.getByText('3 of 4 drives with a full 90 days of prices.')).toBeVisible();
    // Unlike Prices, which ranks by what you pay: shipping is often not known.
    expect(typical.getByText('Shipping is left out: many stores don’t say what it costs.')).toBeVisible();
    expect(trends).toHaveBeenCalledExactlyOnceWith(90, null, 7, {});
    // No split asked for, so nothing is split.
    expect(screen.queryByRole('heading', { level: 2, name: /^By / })).not.toBeInTheDocument();
  });

  it('opens on the longest period prices go back over, saying so, and says when a longer one fills', async () => {
    const user = userEvent.setup();
    // Prices go back fifteen days: a fortnight follows drives, a month follows none.
    const since = new Date(checkedAt.getTime() - 15 * 86_400_000).toISOString();
    const trends = vi.fn<DisktrackerApi['trends']>(async (days, by) =>
      ({ days, by, market: days <= 15 ? market : series(0, 4), parts: [], since }));
    const typical = await open(trends);
    await waitFor(() => expect(trends).toHaveBeenLastCalledWith(14, null, 7, {}));
    const period = within(typical.getByRole('group', { name: 'Period' }));
    expect(period.getByRole('button', { name: '14 days' })).toHaveAttribute('aria-pressed', 'true');
    expect(await typical.findByText('Over the last 14 days, the longest there is: prices go back to Sep 7.')).toBeVisible();
    expect(window.location.search).toBe('');
    await user.click(period.getByRole('button', { name: '90 days' }));
    expect(await typical.findByText('No drive has prices going back 90 days yet: prices go back to Sep 7, so a 90-day trend starts on Dec 6.')).toBeVisible();
    // Chosen, a period is kept.
    expect(window.location.search).toBe('?days=90');
  });

  it('follows only the drives the prices page was narrowed to, says which, and leads back to them or to every drive', async () => {
    const trends = answering(), pricesToday = vi.fn<DisktrackerApi['pricesToday']>(async () => []);
    window.history.replaceState(null, '', '/trends?q=exos&capacity=18000&condition=new');
    renderApp({ trends, pricesToday });
    const scope = { q: 'exos', capacity: [18000], condition: ['new'] };
    await waitFor(() => expect(trends).toHaveBeenLastCalledWith(90, null, 7, scope));
    expect(pricesToday).toHaveBeenLastCalledWith(7, scope);
    const narrowed = within(await screen.findByRole('region', { name: 'Drives followed' }));
    expect(narrowed.getByText('Drives matching “exos”, New, 18 TB.')).toBeVisible();
    expect(narrowed.getByRole('link', { name: 'See these drives' })).toHaveAttribute('href', '/?q=exos&capacity=18000&condition=new');
    expect(narrowed.getByRole('link', { name: 'Every drive' })).toHaveAttribute('href', '/trends');
  });

  it('looks back over the period chosen and keeps it in the URL', async () => {
    const user = userEvent.setup(), trends = answering();
    await open(trends);
    // The period belongs to the chart it sits in, not to the page: today's prices below have no period.
    const period = within(within(screen.getByRole('region', { name: 'Typical item price per TB' })).getByRole('group', { name: 'Period' }));
    expect(within(screen.getByRole('region', { name: 'Typical item price per TB' })).getByRole('group', { name: 'Split by' })).toBeVisible();
    expect(period.getByRole('button', { name: '90 days' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(period.getByRole('button', { name: '180 days' }));
    await waitFor(() => expect(trends).toHaveBeenLastCalledWith(180, null, 7, {}));
    expect(period.getByRole('button', { name: '180 days' })).toHaveAttribute('aria-pressed', 'true');
    expect(window.location.search).toBe('?days=180');
  });

  it('splits by capacity into a chart for each size, each leading to its drives, and says when a size has too few drives to call typical', async () => {
    const user = userEvent.setup(), trends = answering();
    await open(trends);
    await user.click(within(screen.getByRole('group', { name: 'Split by' })).getByRole('button', { name: 'Capacity' }));
    expect(await screen.findByRole('heading', { level: 2, name: 'By capacity' })).toBeVisible();
    expect(trends).toHaveBeenLastCalledWith(90, 'capacity', 7, {});
    expect(window.location.search).toBe('?by=capacity');
    const ten = within(screen.getByRole('region', { name: '10 TB' }));
    expect(ten.getByText('$10.00')).toBeVisible();
    expect(ten.getByText(/20\.0% in 90d/)).toHaveTextContent('↓ Down 20.0% in 90d, 3 drives');
    expect(ten.getByRole('link', { name: 'See drives' })).toHaveAttribute('href', '/?capacity=10000');
    // One drive is that drive's price, not a typical one: no figure is claimed for it.
    const eighteen = within(screen.getByRole('region', { name: '18 TB' }));
    expect(eighteen.getByText('1 drive, too few')).toBeVisible();
    expect(eighteen.queryByText('$20.00')).not.toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: '960 GB' })).getByText('No 90-day history.')).toBeVisible();
  });

  it('splits by store as how far each sits from the typical price of the drives it shares, named as the app names stores', async () => {
    const trends = answering();
    await open(trends, '/trends?by=store');
    expect(await screen.findByRole('heading', { level: 2, name: 'By store, against typical price' })).toBeVisible();
    expect(screen.getByText('Each store against the typical price for the same drives. Below zero is cheaper.')).toBeVisible();
    const ghd = within(screen.getByRole('region', { name: 'GoHardDrive' }));
    expect(ghd.getByText('+6.1%')).toBeVisible();
    expect(ghd.getByText(/3\.0 pts in 90d/)).toHaveTextContent('↓ Down 3.0 pts in 90d, 4 drives');
    expect(ghd.getByRole('link', { name: 'See drives' })).toHaveAttribute('href', '/?store=goharddrive');
    expect(within(screen.getByRole('region', { name: 'ServerPartDeals' })).getByText('2 drives, too few')).toBeVisible();
    expect(within(screen.getByRole('region', { name: 'Western Digital' })).getByText('No shared drives to compare.')).toBeVisible();
  });

  it('restores the period and split from the URL, naming a condition as the app names it', async () => {
    const trends = answering();
    await open(trends, '/trends?by=condition&days=30');
    expect(trends).toHaveBeenCalledExactlyOnceWith(30, 'condition', 7, {});
    expect(within(screen.getByRole('group', { name: 'Split by' })).getByRole('button', { name: 'Condition' })).toHaveAttribute('aria-pressed', 'true');
    const recertified = within(await screen.findByRole('region', { name: 'Recertified' }));
    expect(recertified.getByText('$11.00')).toBeVisible();
    expect(recertified.getByRole('link', { name: 'See drives' })).toHaveAttribute('href', '/?condition=manufacturer_recertified');
  });

  it('counts every drive in stock today along one ruler of price, drives near the same price together, and opens on the prices page the cheapest where one is chosen', async () => {
    const user = userEvent.setup();
    // Today's prices as the server reports them: the 18 TB drive is cheapest by the terabyte.
    const pricesToday = vi.fn<DisktrackerApi['pricesToday']>(async () => [
      mark('Large drive', 18000, 1100, true), mark('Small drive', 12000, 1250), mark('Pricey drive', 20000, 1250),
    ]);
    window.history.replaceState(null, '', '/trends');
    renderApp({ trends: answering(), pricesToday });
    const rail = within(await screen.findByRole('region', { name: 'Prices today' }));
    expect(pricesToday).toHaveBeenCalledWith(7, {});
    expect(within(rail.getByRole('group', { name: 'Drives by price per TB' })).getAllByRole('button').map(button => button.getAttribute('aria-label')))
      .toEqual(['Large drive 18 TB, new, $11.00 per TB', '2 drives, $12.50 to $12.63 per TB, cheapest Small drive 12 TB at $12.50']);
    expect(rail.getByRole('status')).toHaveTextContent('Lowest in stock' + '$11.00 per TB' + 'Large drive 18 TB, New');
    await user.click(rail.getByRole('button', { name: /^2 drives/ }));
    expect(window.location.pathname).toBe('/');
    expect(await screen.findByRole('dialog', { name: 'Small drive' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Prices' })).toHaveAttribute('aria-current', 'page');
  });

  it('says when nothing can be said of today, and when the trends could not be loaded, loading them again on request', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    const trends = vi.fn<DisktrackerApi['trends']>(async (days, by) => {
      attempts += 1;
      if (attempts === 1) throw new Error('Unable to save or load listings (503).');
      return { days, by, market: series(0, 0), parts: [], since: null };
    });
    window.history.replaceState(null, '', '/trends');
    renderApp({ trends });
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Trends could not be loaded');
    expect(alert).toHaveTextContent('Unable to save or load listings (503).');
    await user.click(within(alert).getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('No prices have been recorded yet.')).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('draws the ruler in bands however many drives there are, with the few far dearer than the rest gathered past its end as More', async () => {
    // 150 drives from $10.00 to $24.90 a terabyte, and an 8 GB tape drive at $639,375 a terabyte.
    const many = Array.from({ length: 150 }, (_, index) => mark(`Drive ${index}`, 18000, 1000 + index * 10, index === 0));
    const tape = mark('LTO-8 tape drive', 8, 63_937_500);
    window.history.replaceState(null, '', '/trends');
    renderApp({ trends: answering(), pricesToday: async () => [...many, tape] });
    const rail = within(await screen.findByRole('region', { name: 'Prices today' }));
    // A band can hold many drives, so there are never more bars than bands.
    expect(within(rail.getByRole('group', { name: 'Drives by price per TB' })).getAllByRole('button').length).toBeLessThanOrEqual(41);
    expect(rail.getByRole('button', { name: 'LTO-8 tape drive 8 GB, new, $639,375.00 per TB' })).toHaveClass('over');
    // The ruler ends where all but the dearest hundredth of drives are, not at the dearest.
    const ticks = [...(await screen.findByRole('region', { name: 'Prices today' })).querySelectorAll('.rail-axis span')].map(tick => tick.textContent);
    expect(ticks).toEqual(['$10', '$15', '$20', '$25', 'More']);
  });

  it('asks for today\'s prices once, not again while the trends are looked at', async () => {
    const user = userEvent.setup(), trends = answering();
    const pricesToday = vi.fn<DisktrackerApi['pricesToday']>(async () => [mark('Large drive', 18000, 1100, true)]);
    window.history.replaceState(null, '', '/trends');
    renderApp({ trends, pricesToday });
    await screen.findByRole('region', { name: 'Prices today' });
    await user.click(within(screen.getByRole('group', { name: 'Period' })).getByRole('button', { name: '180 days' }));
    await waitFor(() => expect(trends).toHaveBeenLastCalledWith(180, null, 7, {}));
    expect(pricesToday).toHaveBeenCalledTimes(1);
  });

});
