import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Condition, ListingsApi } from '../../src/api';
import { emptySpecifications } from '../../src/specifications';
import { checkedAt, makeDrive, makeListing, makeUnmatched, shoppingListings, historyPrices } from '../fixtures/listings';
import { memoryStorage, namesIn, renderApp } from '../fixtures/render-app';

afterEach(() => { cleanup(); window.history.replaceState(null, '', '/'); });

function visibleNames() {
  return namesIn('Drive prices');
}

describe('App shopping view', () => {
  it('lists a row per drive with $/TB ahead of the total, what shipping adds, and how long ago it was checked', async () => {
    const user = userEvent.setup();
    const ago = (hours: number) => new Date(checkedAt.getTime() - hours * 3_600_000).toISOString();
    const stale = makeListing('Stale drive', { last_checked_at: ago(240) },
      { observed_at: ago(720), item_price_cents: 18000, shipping_cents: 1250, total_cents: 19250, price_per_tb: '10.69' });
    const soldOut = makeListing('Sold out drive', {}, { in_stock: false, total_cents: 19800, price_per_tb: '11.00' });
    const fresh = makeListing('Fresh drive', { last_checked_at: ago(3) },
      { shipping_cents: null, shipping_known: false, total_cents: 21600, price_per_tb: '12.00' });
    renderApp({ list: async () => [stale, soldOut, fresh] });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getAllByRole('columnheader').map(header => header.textContent))
      .toEqual(['Drive', 'Capacity', 'Condition', '$/TB ↑', 'Total', 'Checked']);
    expect(screen.getByText('3 drives · 3 offers')).toBeVisible();
    const row = (name: string) => within(table.getByRole('button', { name }).closest('tr')!);
    expect(row('Stale drive').getAllByRole('cell').map(cell => cell.textContent))
      .toEqual(['Stale drive' + 'MPN unconfirmed' + 'Example seller', '18 TB', 'New', '$10.69', '$192.50' + '+$12.50 shipping', '10 days ago' + 'Stale']);
    expect(row('Sold out drive').getByText('Free shipping')).toBeVisible();
    expect(row('Sold out drive').getByText('Out of stock')).toBeVisible();
    expect(row('Sold out drive').getByText('under an hour ago')).toBeVisible();
    expect(row('Fresh drive').getByText('Shipping not included')).toBeVisible();
    expect(row('Fresh drive').getByText('3 hours ago')).toHaveAttribute('datetime', ago(3));
    expect(row('Fresh drive').getByText('Lowest $/TB')).toBeVisible();
    await user.click(table.getByRole('button', { name: 'Checked' }));
    expect(visibleNames()).toEqual(['Stale drive', 'Fresh drive', 'Sold out drive']);
    expect(new URLSearchParams(window.location.search).get('sort')).toBe('checked-asc');
    // Anywhere on a row opens the drive, not only its name.
    await user.click(row('Stale drive').getByText('10 days ago'));
    expect(screen.getByRole('dialog', { name: 'Stale drive' })).toBeVisible();
  });

  it('narrows by normalized store, finds drives by alias or seller name, and can hide sold-out offers', async () => {
    const user = userEvent.setup();
    const ultrastar = makeDrive('WUH721816AL5205', { aliases: ['0HNHWC'] });
    const direct = makeListing('Ultrastar direct', { drive: ultrastar, mpn: ultrastar.mpn, store: 'serverpartdeals', seller: '' });
    const store = makeListing('Exos at Beach Audio', { drive: makeDrive('ST18000NM000J'), mpn: 'ST18000NM000J', store: 'other', seller: 'Beach Audio' });
    const soldOut = makeListing('Sold out drive', { drive: makeDrive('ST20000NM007D'), mpn: 'ST20000NM007D', store: 'goharddrive', seller: '' }, { in_stock: false });
    renderApp({ list: async () => [direct, store, soldOut] });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'More filters' }));
    await user.click(screen.getByRole('textbox', { name: 'Store' }));
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['ServerPartDeals', 'GoHardDrive', 'Western Digital', 'Other']);
    await user.click(screen.getByRole('option', { name: 'Other' }));
    expect(visibleNames()).toEqual(['Exos at Beach Audio']);
    expect(new URLSearchParams(window.location.search).getAll('store')).toEqual(['other']);
    expect(screen.getByRole('button', { name: 'More filters (1)' })).toBeVisible();
    // Each active filter is a chip that takes it off again.
    await user.click(within(screen.getByLabelText('Active filters')).getByRole('button', { name: 'Remove filter: Other' }));
    expect(visibleNames()).toHaveLength(3);
    expect(screen.queryByLabelText('Active filters')).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Search drives'), '0hnhwc');
    expect(visibleNames()).toEqual(['Ultrastar direct']);
    await user.clear(screen.getByLabelText('Search drives'));
    await user.type(screen.getByLabelText('Search drives'), 'beach audio');
    expect(visibleNames()).toEqual(['Exos at Beach Audio']);
    await user.clear(screen.getByLabelText('Search drives'));
    await user.click(screen.getByLabelText('In stock only'));
    expect(visibleNames().sort()).toEqual(['Exos at Beach Audio', 'Ultrastar direct']);
    expect(new URLSearchParams(window.location.search).get('stock')).toBe('1');
  }, 15000);

  it('says the drives could not be loaded, and loads them again on request', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    renderApp({ list: async () => {
      attempts += 1;
      if (attempts === 1) throw new Error('Unable to save or load listings (503).');
      return shoppingListings;
    } });
    expect(screen.getByRole('status')).toHaveTextContent('Loading drives…');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Unable to save or load listings (503).');
    // Nothing loaded is not the same as nothing recorded.
    expect(screen.queryByText(/No drives yet/)).not.toBeInTheDocument();
    await user.click(within(alert).getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('table', { name: 'Drive prices' })).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('invites the first offer when nothing is recorded yet', async () => {
    const user = userEvent.setup();
    renderApp({ list: async () => [] });
    expect(await screen.findByText('No drives yet.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Add your first offer' }));
    expect(screen.getByRole('dialog', { name: 'Add offer' })).toBeVisible();
  });

  it('filters by the capacities loaded, picked from a searchable list with how many drives each has, kept in the URL', async () => {
    const user = userEvent.setup();
    const app = renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(screen.queryByLabelText('Minimum capacity (TB)')).not.toBeInTheDocument();
    const capacity = screen.getByRole('textbox', { name: 'Capacity' });
    await user.click(capacity);
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent)).toEqual(['12 TB (1)', '18 TB (1)', '20 TB (1)']);
    await user.click(screen.getByRole('option', { name: '12 TB (1)' }));
    await user.type(capacity, '20');
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent)).toEqual(['20 TB (1)']);
    await user.click(screen.getByRole('option', { name: '20 TB (1)' }));
    expect(visibleNames().sort()).toEqual(['Pricey drive', 'Small drive']);
    expect(new URLSearchParams(window.location.search).getAll('capacity')).toEqual(['12000', '20000']);
    expect(screen.getByLabelText('Active filters')).toHaveTextContent('12 TB');
    app.unmount();
    renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(visibleNames().sort()).toEqual(['Pricey drive', 'Small drive']);
  });

  it('filters by brand, listed from the drives loaded, with drives of no known brand under Unknown', async () => {
    const user = userEvent.setup();
    const listings = [
      makeListing('Exos X18', { drive: makeDrive('ST18000NM000J', { brand: 'Seagate' }) }),
      makeListing('Exos X20', { drive: makeDrive('ST20000NM007D', { brand: 'Seagate' }) }),
      makeListing('Ultrastar HC550', { drive: makeDrive('WUH721818ALE6L4', { brand: 'Western Digital' }) }),
      makeListing('Mystery drive', { drive: makeDrive('X1', { brand: null }) }),
    ];
    renderApp({ list: async () => listings });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'More filters' }));
    await user.click(screen.getByRole('textbox', { name: 'Brand' }));
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent)).toEqual(['Seagate (2)', 'Western Digital (1)', 'Unknown (1)']);
    await user.click(screen.getByRole('option', { name: 'Western Digital (1)' }));
    await user.click(screen.getByRole('option', { name: 'Unknown (1)' }));
    expect(visibleNames().sort()).toEqual(['Mystery drive', 'Ultrastar HC550']);
    expect(new URLSearchParams(window.location.search).getAll('brand')).toEqual(['Western Digital', 'unknown']);
    expect(screen.getByLabelText('Active filters')).toHaveTextContent('Western Digital');
  });

  it('applies a maximum total like every other filter, once typing pauses or at once on Enter', async () => {
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    const total = screen.getByLabelText('Maximum total (USD)');
    await user.type(total, '180');
    await waitFor(() => expect(visibleNames()).toEqual(['Small drive']));
    expect(new URLSearchParams(window.location.search).get('maxTotal')).toBe('180');
    await user.clear(total);
    await user.type(total, '210{Enter}');
    expect(visibleNames().sort()).toEqual(['Large drive', 'Small drive']);
    expect(new URLSearchParams(window.location.search).get('maxTotal')).toBe('210');
  });

  it('keeps the filters used most in view, and counts the rest on More filters', async () => {
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    const filters = within(screen.getByRole('region', { name: 'Filter drives' }));
    const shown = () => [...filters.getAllByRole('textbox'), ...filters.getAllByRole('combobox')]
      .map(field => (field as HTMLInputElement).labels?.[0]?.textContent);
    expect(shown().sort()).toEqual(['Capacity', 'Maximum total (USD)', 'Media type', 'Search drives']);
    expect(filters.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument();
    await user.click(within(filters.getByRole('group', { name: 'Condition' })).getByRole('button', { name: /^New/ }));
    expect(new URLSearchParams(window.location.search).getAll('condition')).toEqual(['new']);
    await user.click(filters.getByRole('button', { name: 'More filters' }));
    expect(shown()).toEqual(expect.arrayContaining(['Brand', 'Store', 'Form factor', 'Interface', 'Recording type', 'Intended use']));
    await user.selectOptions(filters.getByLabelText('Interface', { exact: true }), 'sata');
    await user.click(filters.getByLabelText('In stock only'));
    expect(filters.getByRole('button', { name: 'More filters (2)' })).toHaveAttribute('aria-expanded', 'true');
    await user.click(filters.getByRole('button', { name: 'Clear filters' }));
    expect(window.location.search).toBe('');
  });

  it('shows every kind of storage in one table, filtered by media type, with small capacities in GB', async () => {
    const user = userEvent.setup();
    const specs = (media_type: string, form_factor: string) => ({ ...emptySpecifications(), media_type, form_factor });
    const hdd = makeDrive('ST18000NM000J', { specifications: specs('hdd', '3_5') });
    const card = makeDrive('SDSQXAA-128G', { capacity_gb: 128, specifications: specs('flash_card', 'microsd') });
    renderApp({ list: async () => [
      makeListing('Exos X18', { drive: hdd, mpn: hdd.mpn }),
      makeListing('Extreme 128GB', { drive: card, mpn: card.mpn, capacity_gb: 128 }),
    ] });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getByText('128 GB')).toBeVisible();
    expect(table.getByText('18 TB')).toBeVisible();
    expect(within(screen.getByLabelText('Media type')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Any', 'Hard drive', 'SSD', 'Flash card', 'Unknown']);
    await user.selectOptions(screen.getByLabelText('Media type'), 'flash_card');
    expect(visibleNames()).toEqual(['Extreme 128GB']);
    expect(new URLSearchParams(window.location.search).get('media')).toBe('flash_card');
    expect(screen.getByLabelText('Active filters')).toHaveTextContent('Media type: Flash card');
  });

  it('shares specifications across every listing for the same drive, and restores specification filters from the URL', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D', { specifications: { ...emptySpecifications(), interface: 'sata', recording_type: 'cmr', intended_use: ['nas'] } });
    const listings = [
      makeListing('Verified drive', { drive, mpn: drive.mpn, seller: 'ServerPartDeals' }),
      makeListing('Other seller', { drive, mpn: drive.mpn, seller: 'GoHardDrive' }, { total_cents: 99999, price_per_tb: '99.99' }),
      makeListing('Unrelated drive'),
    ];
    const app = renderApp({ list: async () => listings });
    await user.click(await screen.findByRole('button', { name: 'Verified drive' }));
    expect(screen.getByText('MPN ST18000NM003D · 2 stores · 2 offers')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Specifications' }));
    const details = within(screen.getByRole('region', { name: 'Drive specifications' }));
    expect(details.getByText('SATA')).toBeVisible();
    expect(details.getByText('CMR')).toBeVisible();
    await user.keyboard('{Escape}');
    await user.click(screen.getByRole('button', { name: 'More filters' }));
    await user.selectOptions(screen.getByLabelText('Recording type', { exact: true }), 'cmr');
    expect(visibleNames()).toEqual(['Verified drive']);
    expect(new URLSearchParams(window.location.search).get('recording')).toBe('cmr');
    app.unmount();
    renderApp({ list: async () => listings });
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(visibleNames()).toEqual(['Verified drive']);
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(visibleNames()).toHaveLength(2);
  }, 15000);

  it("says when a drive's prices could not be loaded", async () => {
    const user = userEvent.setup();
    renderApp({ priceHistory: async () => { throw new Error('Unable to save or load listings (503).'); } });
    await user.click(await screen.findByRole('button', { name: 'Small drive' }));
    const details = within(screen.getByRole('dialog', { name: 'Small drive' }));
    expect(await details.findByRole('alert')).toHaveTextContent('Unable to save or load listings (503).');
    expect(details.queryByText('Loading prices…')).not.toBeInTheDocument();
  });

  it('shows the listings a page at a time, and a change of order starts again from the first page', async () => {
    const user = userEvent.setup();
    const drives = Array.from({ length: 60 }, (_, index) => makeListing(`Drive ${String(index + 1).padStart(3, '0')}`, {},
      { total_cents: 10000 + index, price_per_tb: (10 + index / 100).toFixed(2) }));
    renderApp({ list: async () => drives });
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(namesIn('Drive prices')).toEqual(drives.slice(0, 50).map(listing => listing.title));
    const pages = within(screen.getByRole('navigation', { name: 'Drives pages' }));
    expect(pages.getByText('1–50 of 60')).toBeVisible();
    await user.click(pages.getByRole('button', { name: 'Next page' }));
    expect(namesIn('Drive prices')).toEqual(drives.slice(50).map(listing => listing.title));
    await user.click(screen.getByRole('button', { name: /\$\/TB/ }));
    expect(namesIn('Drive prices')).toHaveLength(50);
    expect(pages.getByText('1–50 of 60')).toBeVisible();
  }, 20000);

  it('shows as many listings per page as chosen, starting again from the first page', async () => {
    const user = userEvent.setup();
    const storage = memoryStorage();
    const drives = Array.from({ length: 60 }, (_, index) => makeListing(`Drive ${String(index + 1).padStart(3, '0')}`, {},
      { total_cents: 10000 + index, price_per_tb: (10 + index / 100).toFixed(2) }));
    renderApp({ list: async () => drives }, '/', storage);
    await screen.findByRole('table', { name: 'Drive prices' });
    const pages = within(screen.getByRole('navigation', { name: 'Drives pages' }));
    await user.click(pages.getByRole('button', { name: 'Next page' }));
    await user.selectOptions(screen.getByLabelText('Drives rows per page', { exact: true }), '25');
    expect(namesIn('Drive prices')).toEqual(drives.slice(0, 25).map(listing => listing.title));
    expect(pages.getByText('1–25 of 60')).toBeVisible();
    expect(storage.getItem('disktracker.page-size.listings')).toBe('25');
  }, 20000);

  it('leaves corrections and the review queue to the admin page, keeping Record price', async () => {
    const user = userEvent.setup();
    const listing = makeListing('History drive', { observations: historyPrices, latest: historyPrices[1] });
    renderApp({ list: async () => [listing], listUnmatched: async () => [makeUnmatched('waiting')] });
    await user.click(await screen.findByRole('button', { name: 'History drive' }));
    const details = within(screen.getByRole('dialog', { name: 'History drive' }));
    expect(details.getByRole('button', { name: 'Record price' })).toBeVisible();
    expect(details.queryByRole('button', { name: /More actions/ })).not.toBeInTheDocument();
    expect(details.queryByRole('button', { name: 'Edit specifications' })).not.toBeInTheDocument();
    await user.click(details.getByRole('button', { name: 'Price history (2)' }));
    expect(details.queryByRole('button', { name: 'Delete price' })).not.toBeInTheDocument();
    expect(within(details.getByRole('table', { name: 'Price history' })).getAllByRole('columnheader').map(header => header.textContent))
      .toEqual(['Store', 'Checked', 'Item', 'Shipping & fees', 'Total', 'Notes']);
    expect(screen.queryByRole('button', { name: /Review queue/ })).not.toBeInTheDocument();
  });
  it('shows one combined price trend across every seller sharing a drive, colored per seller, instead of a chart per listing', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const fromServerPartDeals = makeListing('from-serverpartdeals', { drive, title: 'Seagate Exos X20', seller: 'ServerPartDeals' },
      { total_cents: 49900, price_per_tb: '27.72', observed_at: '2026-09-20T12:00:00Z', entered_at: '2026-09-20T12:00:00Z' });
    const fromEbay = makeListing('from-ebay', { drive, title: 'Seagate Exos X20', seller: 'eBay - drivedeals' },
      { total_cents: 48700, price_per_tb: '27.06', observed_at: '2026-09-21T12:00:00Z', entered_at: '2026-09-21T12:00:00Z' });
    renderApp({ list: async () => [fromServerPartDeals, fromEbay] });
    await user.click(await screen.findByRole('button', { name: 'Seagate Exos X20' }));
    const trend = within(screen.getByRole('region', { name: 'Price trend' }));
    expect(await trend.findAllByTestId('price-chart-point')).toHaveLength(2);
    // Both are new, so the store alone tells them apart.
    expect(trend.getByText('ServerPartDeals')).toBeVisible();
    expect(trend.getByText('eBay - drivedeals')).toBeVisible();
    // The chart moved to the drive level; each listing's own section no longer repeats it.
    expect(screen.queryAllByRole('region', { name: 'Price trend' })).toHaveLength(1);
  });

  it('draws the price trend as one point per offer per day, joined into a line only where an offer has more than one day', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST20000NM001J');
    const price = (id: string, at: string, total: number) => ({ ...historyPrices[0], id, observed_at: at, entered_at: at, item_price_cents: total, shipping_cents: 0, total_cents: total });
    // Two checks on the 14th and one on the 18th: two points and a line between them.
    const tracked = [price('r1', '2026-09-14T10:00:00Z', 60000), price('r2', '2026-09-14T12:00:00Z', 59000), price('r3', '2026-09-18T12:00:00Z', 57900)];
    // Two checks on one day only: a single dot.
    const fresh = [price('n1', '2026-09-18T10:00:00Z', 61900), price('n2', '2026-09-18T12:00:00Z', 61900)];
    const offer = (id: string, condition: Condition, observations: typeof tracked) => makeListing(id,
      { drive, mpn: drive.mpn, title: 'Exos X20z', store: 'serverpartdeals', seller: '', condition, observations, latest: observations[observations.length - 1] });
    renderApp({ list: async () => [offer('refurbished', 'refurbished', tracked), offer('new', 'new', fresh)] });
    await user.click(await screen.findByRole('button', { name: 'Exos X20z' }));
    const trend = screen.getByRole('region', { name: 'Price trend' });
    const lines = () => [...trend.querySelectorAll('.recharts-line-curve')].filter(line => /L/.test(line.getAttribute('d') ?? ''));
    const days = () => [...trend.querySelectorAll('.recharts-xAxis-tick-labels text')].map(tick => tick.textContent);
    const day = (value: string) => new Date(value).toLocaleDateString();
    await user.click(screen.getByRole('radio', { name: /^Refurbished/ }));
    await waitFor(() => expect(within(trend).getAllByTestId('price-chart-point')).toHaveLength(2));
    expect(lines()).toHaveLength(1);
    expect(days()).toEqual([day('2026-09-14T12:00:00Z'), day('2026-09-18T12:00:00Z')]);
    // An offer with one day has nowhere to draw a line to.
    await user.click(screen.getByRole('radio', { name: /^New/ }));
    await waitFor(() => expect(within(trend).getAllByTestId('price-chart-point')).toHaveLength(1));
    expect(lines()).toHaveLength(0);
    expect(days()).toEqual([day('2026-09-18T12:00:00Z')]);
  });

  it('lists one offer row per seller and marks the lowest price, with no separate best-price line', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const fromServerPartDeals = makeListing('from-serverpartdeals', { drive, title: 'Seagate Exos X20', seller: 'ServerPartDeals' },
      { total_cents: 49900, price_per_tb: '27.72' });
    const fromEbay = makeListing('from-ebay', { drive, title: 'Seagate Exos X20', seller: 'eBay - drivedeals' },
      { total_cents: 48700, price_per_tb: '27.06' });
    renderApp({ list: async () => [fromServerPartDeals, fromEbay] });
    await user.click(await screen.findByRole('button', { name: 'Seagate Exos X20' }));
    const detail = within(screen.getByRole('dialog', { name: 'Seagate Exos X20' }));
    expect(detail.queryByText(/Best price/)).not.toBeInTheDocument();
    expect(detail.queryByLabelText('Price measure')).not.toBeInTheDocument();
    const offers = within(detail.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    expect(within(offers[0]).getByText('Lowest price')).toBeVisible();
    expect(within(offers[1]).queryByText('Lowest price')).not.toBeInTheDocument();
    // The chart measures its container after it mounts, so its points appear a render later.
    expect(await within(detail.getByRole('region', { name: 'Price trend' })).findAllByTestId('price-chart-point')).toHaveLength(2);
    expect(offers.map(row => within(row).getAllByRole('cell')[0].textContent)).toEqual(['eBay - drivedeals', 'ServerPartDeals']);
    expect(within(offers[0]).getByText('$487.00')).toBeVisible();
    expect(detail.getAllByRole('button', { name: 'Record price' })).toHaveLength(2);
    expect(within(offers[0]).getByRole('button', { name: 'Record price' })).toBeVisible();
  });

  it("shows each seller's price change in its offer row, with no separate per-seller price section", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const tracked = makeListing('tracked', { drive, title: 'Seagate Exos X20', seller: 'GoHardDrive', observations: historyPrices, latest: historyPrices[1] });
    const other = makeListing('other', { drive, title: 'Seagate Exos X20', seller: 'ServerPartDeals' }, { total_cents: 99999, price_per_tb: '99.99' });
    renderApp({ list: async () => [tracked, other] });
    await user.click(await screen.findByRole('button', { name: 'Seagate Exos X20' }));
    const detail = within(screen.getByRole('dialog', { name: 'Seagate Exos X20' }));
    const offers = within(detail.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    expect(within(offers[0]).getByText('▼ $15.00 (6.5%)')).toBeVisible();
    expect(detail.queryByRole('region', { name: 'Current price' })).not.toBeInTheDocument();
  });

  it("shows each offer's total, $/TB, and check time under its condition", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const unknownShipping = makeListing('spd', { drive, title: 'Seagate Exos X18', seller: 'ServerPartDeals', condition: 'manufacturer_recertified' },
      { item_price_cents: 36999, shipping_cents: 0, total_cents: 36999, price_per_tb: '20.56' });
    const priced = makeListing('newegg', { drive, title: 'Seagate Exos X18', seller: 'Newegg', condition: 'new' },
      { item_price_cents: 52999, total_cents: 52999, price_per_tb: '29.44' });
    renderApp({ list: async () => [unknownShipping, priced] });
    await user.click(await screen.findByRole('button', { name: 'Seagate Exos X18' }));
    const rowFor = (seller: string) => within(within(screen.getByRole('table', { name: 'Offers' })).getByText(seller).closest('tr')!);
    // It opens on the condition of the row chosen: the recertified offer, the cheaper per TB.
    expect(screen.getByRole('radio', { name: /^Manufacturer recertified/ })).toBeChecked();
    expect(rowFor('ServerPartDeals').getByText('$369.99')).toBeVisible();
    await user.click(screen.getByRole('radio', { name: /^New/ }));
    expect(rowFor('Newegg').getByText('$29.44')).toBeVisible();
    expect(rowFor('Newegg').getByText(checkedAt.toLocaleString())).toHaveAttribute('datetime', checkedAt.toISOString());
  });

  it('names each offer by its store, or by the store for Other', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const direct = makeListing('direct', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', store: 'serverpartdeals', seller: '' },
      { total_cents: 36999, price_per_tb: '20.56' });
    const marketplace = makeListing('marketplace', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', store: 'other', seller: 'Beach Audio' },
      { total_cents: 88453, price_per_tb: '49.14' });
    renderApp({ list: async () => [direct, marketplace] });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getByText(/from ServerPartDeals/)).toBeVisible();
    await user.click(table.getByRole('button', { name: 'Seagate Exos X18' }));
    const detail = within(screen.getByRole('dialog', { name: 'Seagate Exos X18' }));
    const offers = within(detail.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    expect(offers.map(row => within(row).getAllByRole('cell')[0].textContent)).toEqual(['ServerPartDeals', 'Beach Audio']);
    expect(await within(detail.getByRole('region', { name: 'Price trend' })).findByText('Beach Audio')).toBeVisible();
    await user.click(detail.getByRole('button', { name: 'Price history (2)' }));
    expect(within(detail.getByRole('table', { name: 'Price history' })).getByText('Beach Audio')).toBeVisible();
  });

  it('marks the lowest in-stock price recorded across every store selling that condition, with how many prices and which dates it covers', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const soldOutCheaper = { ...historyPrices[0], id: 'sold-out', observed_at: '2026-09-16T12:00:00Z', in_stock: false, total_cents: 9900 };
    const direct = makeListing('spd', { drive, mpn: drive.mpn, title: 'Exos X20', store: 'serverpartdeals', seller: '', condition: 'refurbished',
      observations: [historyPrices[0], soldOutCheaper, historyPrices[1]], latest: historyPrices[1] });
    const other = makeListing('ghd', { drive, mpn: drive.mpn, title: 'Exos X20', store: 'goharddrive', seller: '', condition: 'refurbished' },
      { observed_at: '2026-09-20T12:00:00Z', total_cents: 22500 });
    renderApp({ list: async () => [direct, other] });
    await user.click(await screen.findByRole('button', { name: 'Exos X20' }));
    const trend = within(screen.getByRole('region', { name: 'Price trend' }));
    const day = (value: string) => new Date(value).toLocaleDateString();
    expect(await trend.findByText(`Lowest price ${'$215.00'} · ServerPartDeals · ${day(historyPrices[1].observed_at)}`)).toBeVisible();
    expect(trend.getByText(`From 3 in-stock prices, ${day('2026-09-14T12:00:00Z')} to ${day('2026-09-20T12:00:00Z')}`)).toBeVisible();
  });

  it("loads a drive's price history only when the drive is opened", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const offers = [
      makeListing('spd', { drive, mpn: drive.mpn, title: 'Exos X20', store: 'serverpartdeals', seller: '' }),
      makeListing('ghd', { drive, mpn: drive.mpn, title: 'Exos X20', store: 'goharddrive', seller: '' }),
      makeListing('Unrelated drive', { observations: historyPrices, latest: historyPrices[1] }),
    ];
    const priceHistory = vi.fn<ListingsApi['priceHistory']>(async ids => offers.filter(offer => ids.includes(offer.id)));
    renderApp({ list: async () => offers, priceHistory });
    await user.click(await screen.findByRole('button', { name: 'Exos X20' }));
    expect(priceHistory).toHaveBeenCalledTimes(1);
    expect([...priceHistory.mock.calls[0][0]].sort()).toEqual(['ghd', 'spd']);
    expect(await screen.findByRole('button', { name: 'Price history (2)' })).toBeVisible();
  });

  it('chooses conditions with buttons above the list, and names on each row the other conditions the drive is sold in', async () => {
    const user = userEvent.setup();
    const ultrastar = makeDrive('WUH721818ALE604'), exos = makeDrive('ST18000NM000J');
    const offer = (id: string, drive: typeof exos, title: string, store: string, condition: Condition, total: number, price = {}) => makeListing(id,
      { drive, mpn: drive.mpn, title, store, seller: '', condition }, { item_price_cents: total, total_cents: total, price_per_tb: (total / 1800).toFixed(2), ...price });
    renderApp({ list: async () => [
      offer('u-new', ultrastar, 'Ultrastar HC550', 'serverpartdeals', 'new', 45000, { in_stock: false }),
      offer('u-recertified', ultrastar, 'Ultrastar HC550', 'serverpartdeals', 'manufacturer_recertified', 48900),
      offer('u-refurbished', ultrastar, 'Ultrastar HC550', 'goharddrive', 'refurbished', 47000),
      offer('e-new', exos, 'Exos X18', 'serverpartdeals', 'new', 50000),
    ] });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    const conditions = within(screen.getByRole('group', { name: 'Condition' }));
    const pressed = () => conditions.getAllByRole('button').filter(button => button.getAttribute('aria-pressed') === 'true').map(button => button.textContent);
    // Only the conditions there are offers in, each with how many drives are sold in it.
    expect(conditions.getAllByRole('button').map(button => button.textContent)).toEqual(['New (2)', 'Manufacturer recertified (1)', 'Refurbished (1)']);
    expect(pressed()).toEqual([]);
    expect(screen.getByText(/Each drive shows its lowest price in any condition/)).toBeVisible();
    const row = (name: string) => within(table.getByRole('button', { name }).closest('tr')!);
    const others = (name: string) => row(name).getAllByRole('button').slice(1).map(button => button.textContent);
    expect(visibleNames()).toEqual(['Ultrastar HC550', 'Exos X18']);
    expect(row('Ultrastar HC550').getByText('$470.00')).toBeVisible();
    expect(others('Ultrastar HC550')).toEqual(['New Out of stock', 'Manufacturer recertified $489.00']);
    expect(others('Exos X18')).toEqual([]);
    // Another condition named on a row opens the drive on it.
    await user.click(row('Ultrastar HC550').getByRole('button', { name: 'Manufacturer recertified $489.00' }));
    expect(within(screen.getByRole('dialog', { name: 'Ultrastar HC550' })).getByRole('radio', { name: /^Manufacturer recertified/ })).toBeChecked();
    await user.keyboard('{Escape}');

    // Choosing a condition prices and orders every drive by its offers in it.
    await user.click(conditions.getByRole('button', { name: 'New (2)' }));
    expect(pressed()).toEqual(['New (2)']);
    expect(new URLSearchParams(window.location.search).getAll('condition')).toEqual(['new']);
    expect(screen.getByText(/Each drive shows its lowest price in New\b/)).toBeVisible();
    expect(visibleNames()).toEqual(['Ultrastar HC550', 'Exos X18']);
    expect(row('Ultrastar HC550').getByText('$450.00')).toBeVisible();
    expect(row('Ultrastar HC550').getByText('Out of stock')).toBeVisible();
    expect(others('Ultrastar HC550')).toEqual([]);
    await user.click(conditions.getByRole('button', { name: 'Refurbished (1)' }));
    expect(screen.getByText(/Each drive shows its lowest price in New or Refurbished/)).toBeVisible();
    expect(row('Ultrastar HC550').getByText('$470.00')).toBeVisible();
    expect(others('Ultrastar HC550')).toEqual(['New Out of stock']);
    // The buttons already show what is chosen, so they are not repeated as chips; Clear filters lets go of them.
    expect(screen.queryByLabelText('Active filters')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(pressed()).toEqual([]);
    expect(window.location.search).toBe('');
  }, 20000);

  it('keeps each condition of a drive apart: its own offers, lowest price, trend and history, switched between at the top', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('WUH721818ALE604');
    const offer = (id: string, store: string, condition: Condition, total: number, fields = {}, price = {}) => makeListing(id,
      { drive, mpn: drive.mpn, title: 'Ultrastar HC550', store, seller: '', condition, ...fields },
      { item_price_cents: total, total_cents: total, price_per_tb: (total / 1800).toFixed(2), ...price });
    const earlier = { ...historyPrices[0], id: 'earlier', observed_at: '2026-09-14T12:00:00Z', total_cents: 50000 };
    const recertified = offer('recertified', 'serverpartdeals', 'manufacturer_recertified', 48900);
    const listings = [
      offer('new', 'serverpartdeals', 'new', 45000, {}, { in_stock: false }),
      { ...recertified, observations: [earlier, recertified.latest] },
      offer('refurbished-spd', 'serverpartdeals', 'refurbished', 48900),
      offer('refurbished-ghd', 'goharddrive', 'refurbished', 47000),
    ];
    renderApp({ list: async () => listings });
    // Four offers from two stores: the row counts stores, as it says.
    expect(await screen.findByText('2 stores')).toBeVisible();
    await user.click(await screen.findByRole('button', { name: 'Ultrastar HC550' }));
    const panel = within(screen.getByRole('dialog', { name: 'Ultrastar HC550' }));
    // One store sells three of the four offers: stores and offers are counted apart.
    expect(panel.getByText('MPN WUH721818ALE604 · 2 stores · 4 offers')).toBeVisible();
    const conditions = within(panel.getByRole('radiogroup', { name: 'Condition' }));
    // Each choice says what that condition costs now, so they can be compared without switching.
    expect(conditions.getAllByRole('radio').map(radio => (radio as HTMLInputElement).labels?.[0].textContent))
      .toEqual(['New' + 'Out of stock', 'Manufacturer recertified' + '$489.00', 'Refurbished' + 'from $470.00']);
    // It opens on the condition of the row chosen: the cheapest in stock, a refurbished one.
    expect(conditions.getByRole('radio', { name: /^Refurbished/ })).toBeChecked();
    const offers = () => within(panel.getByRole('table', { name: 'Offers' }));
    const stores = () => offers().getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent);
    expect(offers().getAllByRole('columnheader').map(header => header.textContent)).toEqual(['Store', '$/TB', 'Total', 'Checked', 'Actions']);
    expect(stores()).toEqual(['GoHardDrive', 'ServerPartDeals']);
    expect(within(offers().getAllByRole('row')[1]).getByText('Lowest price')).toBeVisible();
    const trend = within(panel.getByRole('region', { name: 'Price trend' }));
    expect(await trend.findAllByTestId('price-chart-point')).toHaveLength(2);
    // Within a condition only the store differs, so the store names the line.
    expect(trend.getByText('GoHardDrive')).toBeVisible();
    expect(panel.getByRole('button', { name: 'Price history (2)' })).toBeVisible();

    await user.click(conditions.getByRole('radio', { name: /^Manufacturer recertified/ }));
    expect(stores()).toEqual(['ServerPartDeals']);
    expect(within(offers().getAllByRole('row')[1]).getByText('Lowest price')).toBeVisible();
    expect(trend.getByText(`Lowest price $489.00 · ServerPartDeals · ${checkedAt.toLocaleDateString()}`)).toBeVisible();
    await user.click(panel.getByRole('button', { name: 'Price history (2)' }));
    const history = within(panel.getByRole('table', { name: 'Price history' }));
    expect(history.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent)).toEqual(['ServerPartDeals', 'ServerPartDeals']);

    // A condition that is sold out has no lowest price to claim.
    await user.click(conditions.getByRole('radio', { name: /^New/ }));
    expect(stores()).toEqual(['ServerPartDeals']);
    expect(offers().getByText('Out of stock')).toBeVisible();
    expect(offers().queryByText('Lowest price')).not.toBeInTheDocument();
    expect(trend.queryByText(/Lowest price/)).not.toBeInTheDocument();
    expect(panel.getByRole('button', { name: 'Price history (1)' })).toBeVisible();

    // Filtered to one condition, a row opens on that condition.
    await user.keyboard('{Escape}');
    await user.click(within(screen.getByRole('group', { name: 'Condition' })).getByRole('button', { name: /^Manufacturer recertified/ }));
    await user.click(screen.getByRole('button', { name: 'Ultrastar HC550' }));
    expect(screen.getByRole('radio', { name: /^Manufacturer recertified/ })).toBeChecked();
  }, 20000);

  it('records a price for a new offer identified by MPN, store, seller, and condition, keeping filters when it is hidden', async () => {
    window.history.replaceState(null, '', '/?q=Small');
    const user = userEvent.setup();
    let listings = [...shoppingListings];
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async input => {
      const saved = makeListing('saved', { title: input.title ?? input.mpn, mpn: input.mpn, store: input.store, seller: input.seller,
        condition: input.condition, capacity_gb: input.capacity_gb ?? 0, url: input.url });
      listings = [...listings, saved];
      return saved;
    });
    renderApp({ list: async () => listings, recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    const dialog = screen.getByRole('dialog', { name: 'Add offer' });
    const form = within(dialog);
    const shownFields = () => [...dialog.querySelectorAll('[aria-label]')]
      .filter(field => ['INPUT', 'SELECT', 'TEXTAREA'].includes(field.tagName) && !field.closest('details:not([open])'))
      .map(field => field.getAttribute('aria-label'));
    // The store and its page come first: they are what the copied text is from, and what a later recheck opens.
    expect(shownFields()).toEqual(['Paste from store page', 'Store', 'Store page URL', 'MPN', 'Capacity', 'Condition', 'Item price (USD)', 'Shipping & fees (USD)']);
    expect(within(form.getByLabelText('Condition', { exact: true })).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Choose condition', 'New', 'Manufacturer recertified', 'Refurbished', 'Used']);
    expect(within(form.getByLabelText('Capacity', { exact: true })).getAllByRole('option').map(option => option.textContent))
      .toContain('20 TB');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    expect(within(form.getByLabelText('Store', { exact: true })).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Choose store', 'ServerPartDeals', 'GoHardDrive', 'Western Digital', 'Other']);
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(form.getByText('Enter the MPN.')).toBeVisible();
    expect(form.getByText('Choose a condition.')).toBeVisible();
    expect(form.getByText('Choose a store.')).toBeVisible();
    expect(form.getByText('Enter the item price.')).toBeVisible();
    expect(recordPrice).not.toHaveBeenCalled();
    expect(form.queryByLabelText('Availability')).not.toBeInTheDocument();
    expect(form.queryByLabelText('Fees (USD)')).not.toBeInTheDocument();
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'other');
    expect(shownFields()).toEqual(['Paste from store page', 'Store', 'Seller name', 'Store page URL', 'MPN', 'Capacity', 'Condition', 'Item price (USD)', 'Shipping & fees (USD)']);
    await user.type(form.getByRole('textbox', { name: 'Seller name' }), 'Beach Audio');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'refurbished');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250');
    await user.click(form.getByText('More details'));
    expect(shownFields()).toEqual(['Paste from store page', 'Store', 'Seller name', 'Store page URL', 'MPN', 'Capacity', 'Condition', 'Item price (USD)', 'Shipping & fees (USD)',
      'Offer title', 'Notes']);
    await user.type(form.getByRole('textbox', { name: 'Offer title' }), 'New drive');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(recordPrice).toHaveBeenCalledWith({
      mpn: 'ST20000NM007D', store: 'other', seller: 'Beach Audio', condition: 'refurbished',
      title: 'New drive', url: null, capacity_gb: 20000, item_price_cents: 25000, shipping_cents: 0,
      in_stock: true, observed_at: null, notes: '',
    }, 'save-key');
    expect(await screen.findByText('It is hidden by your filters.')).toBeVisible();
    expect(screen.getByLabelText('Search drives')).toHaveValue('Small');
    expect(visibleNames()).toEqual(['Small drive']);
    await user.click(screen.getByRole('button', { name: 'Show drive' }));
    const details = within(screen.getByRole('dialog', { name: 'New drive' }));
    expect(details.getByRole('table', { name: 'Offers' })).toBeVisible();
    expect(new URLSearchParams(window.location.search).get('q')).toBe('Small');
  });

  it('suggests the MPNs of drives already known while one is typed', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J', { aliases: ['0HNHWC'] });
    const listings = [
      makeListing('Exos X18', { drive, mpn: drive.mpn, capacity_gb: 18000 }),
      makeListing('Exos X20', { drive: makeDrive('ST20000NM007D'), mpn: 'ST20000NM007D', capacity_gb: 20000 }),
    ];
    renderApp({ list: async () => listings });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.type(form.getByLabelText('MPN', { exact: true }), 'st18');
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['ST18000NM000J · Exos X18']);
    await user.click(screen.getByRole('option', { name: 'ST18000NM000J · Exos X18' }));
    expect(form.getByLabelText('MPN', { exact: true })).toHaveValue('ST18000NM000J');
    expect(form.getByText('18 TB, as recorded for this drive')).toBeVisible();
  });

  it('starts each new price with the store and condition last used, even after a reload', async () => {
    const user = userEvent.setup();
    const storage = memoryStorage();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async input => makeListing('saved', { title: input.title ?? 'saved', mpn: input.mpn }));
    const app = renderApp({ recordPrice }, '/', storage);
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    let form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    expect(form.getByLabelText('Store', { exact: true })).toHaveValue('');
    await user.type(form.getByLabelText('MPN', { exact: true }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'refurbished');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Add offer' })).not.toBeInTheDocument());
    app.unmount();
    renderApp({ recordPrice }, '/', storage);
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    expect(form.getByLabelText('Store', { exact: true })).toHaveValue('goharddrive');
    expect(form.getByLabelText('Condition', { exact: true })).toHaveValue('refurbished');
  }, 15000);

  it('saves a price with Enter from any field', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async input => makeListing('saved', { title: input.title ?? 'saved', mpn: input.mpn }));
    renderApp({ recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.type(form.getByLabelText('MPN', { exact: true }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'new');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250{Enter}');
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({ mpn: 'ST20000NM007D', item_price_cents: 25000 }), 'save-key');
  }, 15000);

  it('saves and starts another new price, keeping the store and condition', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async input => makeListing('saved', { title: input.title ?? 'saved', mpn: input.mpn }));
    renderApp({ recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    let form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.type(form.getByLabelText('MPN', { exact: true }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'new');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250');
    await user.click(form.getByRole('button', { name: 'Save and add another' }));
    expect(recordPrice).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(within(screen.getByRole('dialog', { name: 'Add offer' })).getByLabelText('MPN', { exact: true })).toHaveValue(''));
    form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    expect(form.getByLabelText('Item price (USD)', { exact: true })).toHaveValue('');
    expect(form.getByLabelText('Store', { exact: true })).toHaveValue('goharddrive');
    expect(form.getByLabelText('Condition', { exact: true })).toHaveValue('new');
    expect(form.getByRole('status')).toHaveTextContent('Saved saved. Add the next offer.');
  }, 15000);

  it('fills a new price from pasted listing text, for checking before it is saved', async () => {
    const user = userEvent.setup();
    const pasted = 'Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive\n$219.99\nIn stock';
    const readListing = vi.fn<ListingsApi['readListing']>(async () => ({
      title: 'Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive', mpn: 'ST18000NM000J',
      capacity_gb: 18000, condition: 'refurbished', brand: 'Seagate', item_price_cents: 21999,
    }));
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async input => makeListing('saved', { title: input.title ?? 'saved', mpn: input.mpn }));
    renderApp({ readListing, recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.click(form.getByRole('textbox', { name: 'Paste from store page' }));
    await user.paste(pasted);
    await user.click(form.getByRole('button', { name: 'Fill in' }));
    expect(readListing).toHaveBeenCalledWith(pasted);
    expect(await form.findByDisplayValue('ST18000NM000J')).toBeVisible();
    expect(form.getByLabelText('Capacity', { exact: true })).toHaveValue('18000');
    expect(form.getByLabelText('Condition', { exact: true })).toHaveValue('refurbished');
    expect(form.getByLabelText('Item price (USD)', { exact: true })).toHaveValue('219.99');
    expect(form.getByRole('status')).toHaveTextContent('Filled in: title, MPN, capacity, condition, price.');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({
      mpn: 'ST18000NM000J', capacity_gb: 18000, condition: 'refurbished', item_price_cents: 21999,
      title: 'Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive',
    }), 'save-key');
  }, 15000);

  it('says what pasted text did not give, and moves to the first field left to fill', async () => {
    const user = userEvent.setup();
    const readListing = vi.fn<ListingsApi['readListing']>(async () => ({
      title: 'Exos X18 hard drive', mpn: 'ST18000NM000J', capacity_gb: null, condition: null, brand: null, item_price_cents: 21999,
    }));
    renderApp({ readListing });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.type(form.getByRole('textbox', { name: 'Paste from store page' }), 'Exos X18 hard drive $219.99');
    await user.click(form.getByRole('button', { name: 'Fill in' }));
    expect(await form.findByRole('status')).toHaveTextContent('Filled in: title, MPN, price. Not found: capacity, condition.');
    expect(form.getByLabelText('Capacity', { exact: true })).toHaveFocus();
    // Nothing recognisable is said too, rather than leaving the form looking untouched.
    readListing.mockResolvedValueOnce({ title: null, mpn: null, capacity_gb: null, condition: null, brand: null, item_price_cents: null });
    await user.click(form.getByRole('button', { name: 'Fill in' }));
    await waitFor(() => expect(form.getByRole('status')).toHaveTextContent('Nothing could be read from that text. Not found: title, MPN, capacity, condition, price.'));
  }, 15000);

  it("records a later price for an existing offer from its row, keeping that offer's identity", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const offer = makeListing('offer', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', store: 'serverpartdeals', seller: '',
      condition: 'manufacturer_recertified', url: 'https://example.com/x18', capacity_gb: 18000 });
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => offer);
    renderApp({ list: async () => [offer], recordPrice });
    await user.click(await screen.findByRole('button', { name: 'Seagate Exos X18' }));
    const offers = within(screen.getByRole('table', { name: 'Offers' }));
    const [row] = offers.getAllByRole('row').slice(1);
    // The price is typed in the panel itself, under the offer: no second window opens over it.
    expect(offers.queryByRole('textbox')).not.toBeInTheDocument();
    await user.click(within(row).getByRole('button', { name: 'Record price' }));
    expect(within(row).getByRole('button', { name: 'Record price' })).toHaveAttribute('aria-expanded', 'true');
    expect(offers.getByRole('link', { name: /Open store page/ })).toHaveAttribute('href', 'https://example.com/x18');
    await user.type(offers.getByRole('textbox', { name: 'New price for Seagate Exos X18' }), '170{Enter}');
    expect(recordPrice).toHaveBeenCalledWith({
      mpn: 'ST18000NM000J', store: 'serverpartdeals', seller: '', condition: 'manufacturer_recertified',
      title: 'Seagate Exos X18', url: 'https://example.com/x18', capacity_gb: null, item_price_cents: 17000,
      shipping_cents: 0, in_stock: true, observed_at: null, notes: '',
    }, 'save-key');
    expect(await screen.findByRole('status')).toHaveTextContent('Recorded $170.00 for Seagate Exos X18.');
    expect(screen.queryByRole('dialog', { name: 'Record price' })).not.toBeInTheDocument();
    await waitFor(() => expect(offers.queryByRole('textbox')).not.toBeInTheDocument());
  });

  it('opens the full form from an offer for a price with its own shipping, date or notes', async () => {
    const user = userEvent.setup();
    const offer = makeListing('offer', { mpn: 'ST18000NM000J', title: 'Seagate Exos X18', store: 'serverpartdeals', seller: '', condition: 'manufacturer_recertified' });
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => offer);
    renderApp({ list: async () => [offer], recordPrice });
    await user.click(await screen.findByRole('button', { name: 'Seagate Exos X18' }));
    await user.click(within(screen.getByRole('table', { name: 'Offers' })).getByRole('button', { name: 'Record price' }));
    await user.click(screen.getByRole('button', { name: 'More options' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    expect(form.getByText('Seagate Exos X18 · ServerPartDeals · Manufacturer recertified')).toBeVisible();
    expect(form.queryByRole('textbox', { name: 'MPN' })).not.toBeInTheDocument();
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '170');
    await user.type(form.getByLabelText('Shipping & fees (USD)', { exact: true }), '9.99');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({ item_price_cents: 17000, shipping_cents: 999 }), 'save-key');
  });

  it("reuses a known drive's capacity when recording a price for its MPN", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const known = makeListing('known', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', capacity_gb: 18000 });
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => known);
    renderApp({ list: async () => [known], recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST18000NM000J');
    expect(form.queryByLabelText('Capacity', { exact: true })).not.toBeInTheDocument();
    expect(form.getByText('18 TB, as recorded for this drive')).toBeVisible();
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    expect(form.queryByRole('textbox', { name: 'Seller name' })).not.toBeInTheDocument();
    await user.click(form.getByText('More details'));
    await user.type(form.getByRole('textbox', { name: 'Offer title' }), 'Exos X18 from GoHardDrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'new');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '529.99');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(recordPrice).toHaveBeenCalledWith({
      mpn: 'ST18000NM000J', store: 'goharddrive', seller: '', condition: 'new', title: 'Exos X18 from GoHardDrive',
      url: null, capacity_gb: null, item_price_cents: 52999, shipping_cents: 0, in_stock: true,
      observed_at: null, notes: '',
    }, 'save-key');
  }, 15000);

  it('shows plain prices with no stock status or unknown amounts anywhere', async () => {
    const user = userEvent.setup();
    const offer = makeListing('Plain drive', {}, { item_price_cents: 18000, shipping_cents: 1250, total_cents: 19250, price_per_tb: '10.69' });
    renderApp({ list: async () => [offer] });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.queryByText(/In stock|Unknown/)).not.toBeInTheDocument();
    expect(table.getByText('$192.50')).toBeVisible();
    expect(screen.queryByLabelText('Availability')).not.toBeInTheDocument();
    await user.click(table.getByRole('button', { name: 'Plain drive' }));
    await user.click(screen.getByRole('button', { name: 'Price history (1)' }));
    const history = within(screen.getByRole('table', { name: 'Price history' }));
    expect(history.getAllByRole('columnheader').map(header => header.textContent))
      .toEqual(['Store', 'Checked', 'Item', 'Shipping & fees', 'Total', 'Notes']);
    expect(history.getByText('$12.50')).toBeVisible();
  });

  it('never marks a sold-out offer as lowest, flags shipping not included, and shows when each offer was last checked', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const soldOut = makeListing('sold', { drive, title: 'Seagate Exos X18', seller: 'Cheap shop' },
      { item_price_cents: 30000, total_cents: 30000, price_per_tb: '16.67', in_stock: false });
    const stocked = makeListing('stocked', { drive, title: 'Seagate Exos X18', seller: 'Pricier shop', last_checked_at: '2026-09-22T11:00:00Z' },
      { item_price_cents: 40000, shipping_cents: null, shipping_known: false, total_cents: 40000, price_per_tb: '22.22',
        observed_at: '2026-09-20T12:00:00Z' });
    renderApp({ list: async () => [soldOut, stocked] });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getByText(/from Pricier shop/)).toBeVisible();
    await user.click(table.getByRole('button', { name: 'Seagate Exos X18' }));
    const offers = within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    const rowFor = (seller: string) => within(offers.find(row => within(row).queryByText(seller))!);
    expect(rowFor('Cheap shop').getByText('Out of stock')).toBeVisible();
    expect(rowFor('Cheap shop').queryByText('Lowest price')).not.toBeInTheDocument();
    expect(rowFor('Pricier shop').getByText('Lowest price')).toBeVisible();
    expect(rowFor('Pricier shop').getByText('Shipping not included')).toBeVisible();
    expect(rowFor('Pricier shop').getByText(new Date('2026-09-22T11:00:00Z').toLocaleString())).toBeVisible();
  });

  it('records that an existing offer is out of stock without needing a new price', async () => {
    const user = userEvent.setup();
    const offer = makeListing('Exos X18', { mpn: 'ST18000NM000J' });
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => offer);
    renderApp({ list: async () => [offer], recordPrice });
    await user.click(await screen.findByRole('button', { name: 'Exos X18' }));
    const offers = within(screen.getByRole('table', { name: 'Offers' }));
    await user.click(offers.getByRole('button', { name: 'Record price' }));
    await user.click(offers.getByRole('button', { name: 'Out of stock' }));
    expect(recordPrice).toHaveBeenCalledWith({
      mpn: 'ST18000NM000J', store: offer.store, seller: offer.seller, condition: offer.condition,
      title: offer.title, url: offer.url, capacity_gb: null, item_price_cents: null, shipping_cents: 0,
      in_stock: false, observed_at: null, notes: '',
    }, 'save-key');
  });

  it('connects filters, sorting, URL state, and Clear filters', async () => {
    const user = userEvent.setup();
    const app = renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.selectOptions(screen.getByLabelText('Sort by'), 'total-asc');
    expect(visibleNames()).toEqual(['Small drive', 'Large drive', 'Pricey drive']);
    await user.type(screen.getByLabelText('Maximum total (USD)'), '180{Enter}');
    expect(visibleNames()).toEqual(['Small drive']);
    expect(new URLSearchParams(window.location.search).get('maxTotal')).toBe('180');
    app.unmount();
    renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(screen.getByLabelText('Maximum total (USD)')).toHaveValue('180');
    expect(screen.getByLabelText('Sort by')).toHaveValue('total-asc');
    expect(visibleNames()).toEqual(['Small drive']);
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(new URLSearchParams(window.location.search).has('maxTotal')).toBe(false);
    await user.selectOptions(screen.getByLabelText('Sort by'), 'unit-asc');
    expect(visibleNames()).toEqual(['Large drive', 'Small drive', 'Pricey drive']);
  });

  it('explains an empty filtered view and offers an explicit reset', async () => {
    window.history.replaceState(null, '', '/?q=does-not-exist');
    renderApp();
    expect(await screen.findByText('No drives match these filters.')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(await screen.findByRole('table', { name: 'Drive prices' })).toBeVisible();
  });
});
