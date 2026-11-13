import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Condition, DisktrackerApi, Market, MarketQuery, Observation } from '../../src/api';
import { emptySpecifications, type SpecValue } from '../../src/specifications';
import { checkedAt, historyPrices, makeDrive, makeOffer, makeReviewItem, recordedOn, shoppingListings } from '../fixtures/listings';
import { memoryStorage, namesIn, renderApp } from '../fixtures/render-app';
import { inventoryPage, foundPage, marketPage, noOptions, pricesOf, rowsOf } from '../fixtures/responses';

afterEach(() => { cleanup(); window.history.replaceState(null, '', '/'); });

function visibleNames() {
  return namesIn('Drive prices');
}

/** A server answering each page of drives as the test says it would, keeping every query asked. */
function server(answer: (query: MarketQuery) => Market) {
  const asked: MarketQuery[] = [];
  const market: DisktrackerApi['market'] = async query => { asked.push(query); return answer(query); };
  return { asked, market };
}

describe('App shopping view', () => {
  it('lists a row per drive with $/TB and its condition ahead of the total, what shipping adds, and how long ago it was checked', async () => {
    const user = userEvent.setup();
    const ago = (hours: number) => new Date(checkedAt.getTime() - hours * 3_600_000).toISOString();
    const stale = makeOffer('Stale drive', { last_checked_at: ago(240) },
      { observed_at: ago(720), item_price_cents: 18000, shipping_cents: 1250, total_cents: 19250, price_per_tb: '10.69' });
    const soldOut = makeOffer('Sold out drive', {}, { in_stock: false, total_cents: 19800, price_per_tb: '11.00' });
    const fresh = makeOffer('Fresh drive', { last_checked_at: ago(3) },
      { shipping_cents: null, shipping_known: false, total_cents: 21600, price_per_tb: '12.00' });
    // The server's order, and the offer it says is the lowest per terabyte.
    const { asked, market } = server(query => marketPage(rowsOf(query.sort === 'checked-asc' ? [stale, fresh, soldOut] : [stale, soldOut, fresh]),
      { lowest: { total: [], unit: ['Fresh drive'] } }));
    renderApp({ listOffers: async () => [stale, soldOut, fresh], market });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getAllByRole('columnheader').map(header => header.textContent))
      .toEqual(['Drive', 'Capacity', '$/TB ↑', 'Total', 'Item price vs low, last' + '30 days90 days180 days', 'Checked']);
    expect(screen.getByText('3 drives, 3 offers')).toBeVisible();
    const row = (name: string) => within(table.getByTitle(name).closest('tr')!);
    expect(row('Stale drive').getAllByRole('cell').map(cell => cell.textContent))
      .toEqual(['18 TB drive' + 'MPN-Stale drive' + 'Example seller', '18 TB', '$10.69' + 'New', '$192.50' + 'incl. $12.50 shipping', '', '10d ago' + 'Stale']);
    // Free shipping is the usual case and goes unsaid: a row speaks of shipping only when it costs or is not known.
    expect(row('Sold out drive').queryByText(/shipping/i)).not.toBeInTheDocument();
    expect(row('Sold out drive').getByText('Out of stock')).toBeVisible();
    expect(row('Sold out drive').getByText('<1h ago')).toBeVisible();
    expect(row('Fresh drive').getByText('+ shipping')).toBeVisible();
    expect(row('Fresh drive').getByText('3h ago')).toHaveAttribute('datetime', ago(3));
    expect(row('Fresh drive').getByText('Lowest $/TB')).toBeVisible();
    await user.click(table.getByRole('button', { name: 'Checked' }));
    expect(asked.at(-1)?.sort).toBe('checked-asc');
    await waitFor(() => expect(visibleNames()).toEqual(['Stale drive', 'Fresh drive', 'Sold out drive']));
    expect(new URLSearchParams(window.location.search).get('sort')).toBe('checked-asc');
    // Anywhere on a row opens the drive, not only its name.
    await user.click(row('Stale drive').getByText('10d ago'));
    expect(screen.getByRole('dialog', { name: '18 TB drive' })).toBeVisible();
  });

  it("pictures where a drive's item price stands against the lowest the server says any store has had it", async () => {
    const drive = makeDrive('ST18000NM000J');
    const offers = [makeOffer('spd', { drive, mpn: drive.mpn, title: 'Exos X18', store: 'serverpartdeals', seller: '' })];
    const range = { today: 18000, low: 17000, high: 19000, average: 18222, days: 90 };
    renderApp({ listOffers: async () => offers, market: async query => marketPage(rowsOf(offers, { [drive.id]: range }), {}, query) });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getByRole('columnheader', { name: /^Item price vs low, last/ })).toBeVisible();
    const pictured = await table.findByRole('img', { name: 'Today $180.00, 5.9% above the lowest. Over 90 days: lowest $170.00, average $182.22, highest $190.00.' });
    expect(within(pictured.closest('td')!).getByText('+5.9% above its low')).toBeVisible();
  });

  it('looks back over 30, 90 or 180 days as chosen in the range column, keeping the choice in the URL and the page it was made on', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const exos = makeOffer('spd', { drive, mpn: drive.mpn, title: 'Exos X18', store: 'serverpartdeals', seller: '' });
    const others = Array.from({ length: 55 }, (_, index) => makeOffer(`Drive ${String(index + 1).padStart(3, '0')}`));
    const ranges = {
      30: { today: 18000, low: 17000, high: 18000, average: 17333, days: 30 },
      90: { today: 18000, low: 17000, high: 19000, average: 18222, days: 90 },
      180: { today: 18000, low: 17000, high: 19000, average: 18300, days: 100 },
    };
    // Dearest per terabyte of 56 drives, so the server puts it on the second page.
    const { asked, market } = server(query => marketPage(rowsOf([...others, exos], { [drive.id]: ranges[query.range_days as 30 | 90 | 180] }), {}, query));
    renderApp({ listOffers: async () => [...others, exos], market });
    await screen.findByRole('table', { name: 'Drive prices' });
    const pages = within(screen.getByRole('navigation', { name: 'Drives pages' }));
    await user.click(pages.getByRole('button', { name: 'Next page' }));
    const table = within(screen.getByRole('table', { name: 'Drive prices' }));
    const period = () => table.getByRole('combobox', { name: 'Days the range looks back over' });
    expect(period()).toHaveValue('90');
    expect(await table.findByRole('img', { name: 'Today $180.00, 5.9% above the lowest. Over 90 days: lowest $170.00, average $182.22, highest $190.00.' })).toBeVisible();
    await user.selectOptions(period(), '30');
    expect(await table.findByRole('img', { name: 'Today $180.00, 5.9% above the lowest. Over 30 days: lowest $170.00, average $173.33, highest $180.00.' })).toBeVisible();
    // The page it was on is asked for again, over the new period.
    expect(asked.at(-1)).toMatchObject({ range_days: 30, offset: 50 });
    expect(pages.getByText('51–56 of 56')).toBeVisible();
    expect(new URLSearchParams(window.location.search).get('days')).toBe('30');
    // Where the table has no headings to hold the choice (a narrow screen), it is offered beside the order.
    await user.selectOptions(screen.getByRole('combobox', { name: 'Compare with the last' }), '180');
    // There are only 100 days of prices to look back over.
    expect(await table.findByRole('img', { name: 'Today $180.00, 5.9% above the lowest. Over 100 days: lowest $170.00, average $183.00, highest $190.00.' })).toBeVisible();
    expect(table.getByText('+5.9% above its low, tracked 100 days')).toBeVisible();
    expect(period()).toHaveValue('180');
  }, 20000);

  it('leaves out drives no store has in stock until they are asked for, saying how many', async () => {
    const user = userEvent.setup();
    const soldOut = makeOffer('Sold out drive', { drive: makeDrive('ST10000NM001G') }, { in_stock: false });
    const cheap = makeOffer('Cheap drive', { drive: makeDrive('ST18000NM000J') });
    const dear = makeOffer('Dear drive', { drive: makeDrive('ST20000NM007D') });
    const { asked, market } = server(query => query.in_stock === false
      ? marketPage(rowsOf([cheap, dear, soldOut]))
      : marketPage(rowsOf([cheap, dear]), { sold_out: 1 }));
    renderApp({ listOffers: async () => [soldOut, dear, cheap], market });
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(asked[0].in_stock).toBeUndefined();
    expect(visibleNames()).toEqual(['Cheap drive', 'Dear drive']);
    expect(screen.getByText('2 drives, 2 offers')).toBeVisible();
    expect(screen.getByText('1 out of stock hidden.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Show' }));
    expect(asked.at(-1)?.in_stock).toBe(false);
    await waitFor(() => expect(visibleNames()).toEqual(['Cheap drive', 'Dear drive', 'Sold out drive']));
    expect(screen.getByText('3 drives, 3 offers')).toBeVisible();
    expect(screen.queryByText(/out of stock hidden/)).not.toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('stock')).toBe('all');
  });

  it('opens a drive beside the table, not over it, when the window is wide enough to keep every column', async () => {
    const user = userEvent.setup();
    // A window at least 1500px wide.
    const matchMedia = (query: string) => ({ matches: query === '(min-width: 1500px)', media: query, addEventListener: () => {}, removeEventListener: () => {} });
    Object.defineProperty(window, 'matchMedia', { configurable: true, value: matchMedia });
    try {
      renderApp();
      await user.click(await screen.findByTitle('Small drive'));
      const panel = within(await screen.findByRole('complementary', { name: '18 TB drive' }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      // The table stays in reach behind nothing: another drive can be opened straight from it.
      await user.click(screen.getByTitle('Large drive'));
      expect(await screen.findByRole('complementary', { name: '18 TB drive' })).toBeVisible();
      expect(panel.queryByRole('heading', { name: 'Small drive' })).not.toBeInTheDocument();
      await user.click(within(screen.getByRole('complementary', { name: '18 TB drive' })).getByRole('button', { name: 'Close' }));
      expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
    } finally { delete (window as Partial<Window>).matchMedia; }
  });

  it('narrows by store, searches by name, and can show sold-out offers, each asked of the server', async () => {
    const user = userEvent.setup();
    const ultrastar = makeDrive('WUH721816AL5205', { aliases: ['0HNHWC'] });
    const direct = makeOffer('Ultrastar direct', { drive: ultrastar, mpn: ultrastar.mpn, store: 'serverpartdeals', seller: '' });
    const store = makeOffer('Exos at Beach Audio', { drive: makeDrive('ST18000NM000J'), mpn: 'ST18000NM000J', store: 'other', seller: 'Beach Audio' });
    const soldOut = makeOffer('Sold out drive', { drive: makeDrive('ST20000NM007D'), mpn: 'ST20000NM007D', store: 'goharddrive', seller: '' }, { in_stock: false });
    const { asked, market } = server(query => marketPage(rowsOf(
      query.store?.includes('other') ? [store]
        : query.q === '0hnhwc' ? [direct]
          : query.q === 'beach audio' ? [store]
            : query.in_stock === false ? [direct, store, soldOut] : [direct, store])));
    renderApp({ listOffers: async () => [direct, store, soldOut], market });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'More filters' }));
    await user.click(screen.getByRole('textbox', { name: 'Store' }));
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['ServerPartDeals', 'GoHardDrive', 'Western Digital', 'Other']);
    await user.click(screen.getByRole('option', { name: 'Other' }));
    expect(asked.at(-1)?.store).toEqual(['other']);
    await waitFor(() => expect(visibleNames()).toEqual(['Exos at Beach Audio']));
    expect(new URLSearchParams(window.location.search).getAll('store')).toEqual(['other']);
    expect(screen.getByRole('button', { name: 'More filters (1)' })).toBeVisible();
    // Each active filter is a chip that takes it off again.
    await user.click(within(screen.getByLabelText('Active filters')).getByRole('button', { name: 'Remove filter: Other' }));
    await waitFor(() => expect(visibleNames()).toHaveLength(2));
    expect(screen.queryByLabelText('Active filters')).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Search drives'), '0hnhwc');
    await waitFor(() => expect(visibleNames()).toEqual(['Ultrastar direct']));
    expect(asked.at(-1)?.q).toBe('0hnhwc');
    await user.clear(screen.getByLabelText('Search drives'));
    await user.type(screen.getByLabelText('Search drives'), 'beach audio');
    await waitFor(() => expect(visibleNames()).toEqual(['Exos at Beach Audio']));
    await user.clear(screen.getByLabelText('Search drives'));
    await waitFor(() => expect(visibleNames().sort()).toEqual(['Exos at Beach Audio', 'Ultrastar direct']));
    expect(asked.at(-1)?.q).toBeUndefined();
    await user.click(screen.getByLabelText('In stock only'));
    await waitFor(() => expect(visibleNames().sort()).toEqual(['Exos at Beach Audio', 'Sold out drive', 'Ultrastar direct']));
    expect(new URLSearchParams(window.location.search).get('stock')).toBe('all');
  }, 15000);

  it('says the drives could not be loaded, and loads them again on request', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    renderApp({ listOffers: async () => {
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
    renderApp({ listOffers: async () => [] });
    expect(await screen.findByText('No drives yet.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Record your first price' }));
    expect(screen.getByRole('dialog', { name: 'Record price' })).toBeVisible();
  });

  it('filters by the capacities the server offers, picked from a searchable list with how many drives each has, kept in the URL', async () => {
    const user = userEvent.setup();
    const capacities = [{ value: 12000, drives: 1 }, { value: 18000, drives: 1 }, { value: 20000, drives: 1 }];
    const [small, large, pricey] = shoppingListings;
    const { asked, market } = server(query => marketPage(rowsOf(query.capacity?.length ? [small, pricey] : [small, large, pricey]),
      { filter_options: { ...noOptions(), capacities } }));
    const app = renderApp({ market });
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(screen.queryByLabelText('Minimum capacity (TB)')).not.toBeInTheDocument();
    const capacity = screen.getByRole('textbox', { name: 'Capacity' });
    await user.click(capacity);
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent)).toEqual(['12 TB (1)', '18 TB (1)', '20 TB (1)']);
    await user.click(screen.getByRole('option', { name: '12 TB (1)' }));
    await user.type(capacity, '20');
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent)).toEqual(['20 TB (1)']);
    await user.click(screen.getByRole('option', { name: '20 TB (1)' }));
    expect(asked.at(-1)?.capacity).toEqual([12000, 20000]);
    await waitFor(() => expect(visibleNames().sort()).toEqual(['Pricey drive', 'Small drive']));
    expect(new URLSearchParams(window.location.search).getAll('capacity')).toEqual(['12000', '20000']);
    expect(screen.getByLabelText('Active filters')).toHaveTextContent('12 TB');
    app.unmount();
    renderApp({ market });
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(asked.at(-1)?.capacity).toEqual([12000, 20000]);
  });

  it('filters by brand, listed as the server counts them, with drives of no known brand under Unknown', async () => {
    const user = userEvent.setup();
    const brands = [{ value: 'Seagate', drives: 2 }, { value: 'Western Digital', drives: 1 }, { value: 'unknown', drives: 1 }];
    const { asked, market } = server(() => marketPage(rowsOf(shoppingListings), { filter_options: { ...noOptions(), brands } }));
    renderApp({ market });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('button', { name: 'More filters' }));
    await user.click(screen.getByRole('textbox', { name: 'Brand' }));
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent)).toEqual(['Seagate (2)', 'Western Digital (1)', 'Unknown (1)']);
    await user.click(screen.getByRole('option', { name: 'Western Digital (1)' }));
    await user.click(screen.getByRole('option', { name: 'Unknown (1)' }));
    expect(asked.at(-1)?.brand).toEqual(['Western Digital', 'unknown']);
    expect(new URLSearchParams(window.location.search).getAll('brand')).toEqual(['Western Digital', 'unknown']);
    expect(screen.getByLabelText('Active filters')).toHaveTextContent('Western Digital');
  });

  it('asks for a maximum total like every other filter, once typing pauses or at once on Enter', async () => {
    const user = userEvent.setup();
    const { asked, market } = server(() => marketPage(rowsOf(shoppingListings)));
    renderApp({ market });
    await screen.findByRole('table', { name: 'Drive prices' });
    const total = screen.getByLabelText('Maximum total (USD)');
    await user.type(total, '180');
    await waitFor(() => expect(asked.at(-1)?.max_total_cents).toBe(18000));
    expect(new URLSearchParams(window.location.search).get('maxTotal')).toBe('180');
    await user.clear(total);
    await user.type(total, '210{Enter}');
    expect(asked.at(-1)?.max_total_cents).toBe(21000);
    expect(new URLSearchParams(window.location.search).get('maxTotal')).toBe('210');
  });

  it('keeps the filters used most in view, and counts the rest on More filters', async () => {
    const user = userEvent.setup();
    const conditions = [{ value: 'new' as const, drives: 3 }];
    renderApp({ market: async query => marketPage(rowsOf(shoppingListings), { filter_options: { ...noOptions(), conditions } }, query) });
    await screen.findByRole('table', { name: 'Drive prices' });
    const filters = within(screen.getByRole('region', { name: 'Filter drives' }));
    const shown = () => [...filters.getAllByRole('textbox'), ...filters.getAllByRole('combobox')]
      .map(field => (field as HTMLInputElement).labels?.[0]?.textContent);
    expect(shown().sort()).toEqual(['Capacity', 'Interface', 'Maximum total (USD)', 'Media type', 'Search drives']);
    expect(filters.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument();
    await user.click(within(filters.getByRole('group', { name: 'Condition' })).getByRole('button', { name: /^New/ }));
    expect(new URLSearchParams(window.location.search).getAll('condition')).toEqual(['new']);
    // The interface is in view with the filters used most, so it is not counted on More filters.
    await user.selectOptions(filters.getByLabelText('Interface', { exact: true }), 'sata');
    expect(new URLSearchParams(window.location.search).get('interface')).toBe('sata');
    expect(filters.getByRole('button', { name: 'More filters' })).toHaveAttribute('aria-expanded', 'false');
    await user.click(filters.getByRole('button', { name: 'More filters' }));
    expect(shown().sort()).toEqual(['Brand', 'Capacity', 'Form factor', 'Intended use', 'Interface', 'Maximum total (USD)', 'Media type', 'Recording type', 'Search drives', 'Store']);
    await user.selectOptions(filters.getByLabelText('Recording type', { exact: true }), 'cmr');
    // In stock only is always in view, so it is not one of the filters counted here.
    await user.click(filters.getByLabelText('In stock only'));
    expect(filters.getByRole('button', { name: 'More filters (1)' })).toHaveAttribute('aria-expanded', 'true');
    await user.click(filters.getByRole('button', { name: 'Clear filters' }));
    expect(window.location.search).toBe('');
  });

  it('names a drive the same in its row and its panel, keeps each store’s own title on its offer, and leads to the store first', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J', { brand: 'Seagate', specifications: { ...emptySpecifications(), media_type: 'hdd', interface: 'sata' } });
    const spd = makeOffer('Seagate ST18000NM000J X18 7200 RPM 18TB Enterprise HDD Refurbished',
      { drive, mpn: drive.mpn, store: 'serverpartdeals', seller: '', url: 'https://spd.test/x18' });
    const ghd = makeOffer('Seagate 18TB Exos X18 ST18000NM000J 7200 RPM SATA 6Gb/s',
      { drive, mpn: drive.mpn, store: 'goharddrive', seller: '', url: 'https://ghd.test/x18' }, { total_cents: 20000, price_per_tb: '11.11' });
    renderApp({ listOffers: async () => [spd, ghd], market: async () => marketPage(rowsOf([spd, ghd])) });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    await user.click(table.getByRole('button', { name: 'Seagate 18 TB SATA hard drive ST18000NM000J' }));
    expect(await screen.findByRole('heading', { name: 'Seagate 18 TB SATA hard drive' })).toBeVisible();
    const offers = within(screen.getByRole('table', { name: 'Offers' }));
    const rowOf = (title: string) => within(offers.getByText(title).closest('tr')!);
    for (const { title, url } of [spd, ghd]) {
      const view = rowOf(title).getByRole('link', { name: 'View at store' });
      expect(view).toHaveAttribute('href', url);
      // Buying comes first; recording what the store asks comes after.
      const record = rowOf(title).getByRole('button', { name: 'Record price' });
      expect(view.compareDocumentPosition(record) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it('records a price from the header, as it is called everywhere', async () => {
    const user = userEvent.setup();
    renderApp();
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    expect(screen.getByRole('dialog', { name: 'Record price' })).toBeVisible();
  });

  it('leads to the trends of the drives the filters narrow to, carrying the filters but not the order or period', async () => {
    window.history.replaceState(null, '', '/?q=exos&condition=new&sort=total-asc&days=30');
    renderApp();
    expect(await screen.findByRole('link', { name: 'Trends for these drives' })).toHaveAttribute('href', '/trends?q=exos&condition=new');
    cleanup();
    window.history.replaceState(null, '', '/');
    renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(screen.queryByRole('link', { name: 'Trends for these drives' })).not.toBeInTheDocument();
  });

  it('says which drives were collected with a capacity or title that may not be right', async () => {
    const huge = makeOffer('Kioxia KPM7XVUG960G 960TB', { capacity_gb: 960000, doubt: 'implausible_capacity' });
    const bundle = makeOffer('HPE R0P90A 48TB (8x6) 6-pack', { capacity_gb: 48000, doubt: 'not_a_single_drive' });
    const plain = makeOffer('Exos X18 18TB');
    renderApp({ listOffers: async () => [huge, bundle, plain], market: async () => marketPage(rowsOf([huge, bundle, plain])) });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    const row = (name: string) => within(table.getByTitle(name).closest('tr')!);
    expect(row('Kioxia KPM7XVUG960G 960TB').getByText('Capacity unverified')).toHaveAttribute('title',
      'Its capacity may have been misread from the store. It waits for a person to check it.');
    expect(row('HPE R0P90A 48TB (8x6) 6-pack').getByText('May not be one drive')).toHaveAttribute('title',
      'Its title reads as several drives, tape or other equipment. It waits for a person to check it.');
    expect(row('Exos X18 18TB').queryByText(/unverified|one drive/)).not.toBeInTheDocument();
  });

  it('shows every kind of storage in one table, asking for a media type, with small capacities in GB', async () => {
    const user = userEvent.setup();
    const specs = (media_type: SpecValue<'media_type'>, form_factor: SpecValue<'form_factor'>) => ({ ...emptySpecifications(), media_type, form_factor });
    const hdd = makeDrive('ST18000NM000J', { specifications: specs('hdd', '3_5') });
    const card = makeDrive('SDSQXAA-128G', { capacity_gb: 128, specifications: specs('flash_card', 'microsd') });
    const exos = makeOffer('Exos X18', { drive: hdd, mpn: hdd.mpn }), extreme = makeOffer('Extreme 128GB', { drive: card, mpn: card.mpn, capacity_gb: 128 });
    const { asked, market } = server(query => marketPage(rowsOf(query.media_type === 'flash_card' ? [extreme] : [exos, extreme])));
    renderApp({ market });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getByText('128 GB')).toBeVisible();
    expect(table.getByText('18 TB')).toBeVisible();
    expect(within(screen.getByLabelText('Media type')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Any', 'Hard drive', 'SSD', 'Flash card', 'Unknown']);
    await user.selectOptions(screen.getByLabelText('Media type'), 'flash_card');
    expect(asked.at(-1)?.media_type).toBe('flash_card');
    await waitFor(() => expect(visibleNames()).toEqual(['Extreme 128GB']));
    expect(new URLSearchParams(window.location.search).get('media')).toBe('flash_card');
    expect(screen.getByLabelText('Active filters')).toHaveTextContent('Media type: Flash card');
  });

  it('shows a drive with the specifications every offer of it shares, and restores specification filters from the URL', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D', { specifications: { ...emptySpecifications(), interface: 'sata', recording_type: 'cmr', intended_use: ['nas'] } });
    const listings = [
      makeOffer('Verified drive', { drive, mpn: drive.mpn, seller: 'ServerPartDeals' }),
      makeOffer('Other seller', { drive, mpn: drive.mpn, seller: 'GoHardDrive' }, { total_cents: 99999, price_per_tb: '99.99' }),
      makeOffer('Unrelated drive'),
    ];
    const { asked, market } = server(query => marketPage(rowsOf(query.recording_type === 'cmr' ? listings.slice(0, 2) : listings)));
    const app = renderApp({ listOffers: async () => listings, market });
    await user.click(await screen.findByTitle('Verified drive'));
    expect(await screen.findByText('ST18000NM003D, 2 stores')).toBeVisible();
    // One condition is nothing to choose between: it is named, not offered as a choice.
    const opened = within(screen.getByRole('dialog', { name: '18 TB SATA drive' }));
    expect(opened.queryByRole('radiogroup', { name: 'Condition' })).not.toBeInTheDocument();
    expect(opened.getByText('New')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Specifications' }));
    const details = within(screen.getByRole('region', { name: 'Drive specifications' }));
    expect(details.getByText('SATA')).toBeVisible();
    expect(details.getByText('CMR')).toBeVisible();
    await user.keyboard('{Escape}');
    await user.click(screen.getByRole('button', { name: 'More filters' }));
    await user.selectOptions(screen.getByLabelText('Recording type', { exact: true }), 'cmr');
    await waitFor(() => expect(visibleNames()).toEqual(['Verified drive']));
    expect(new URLSearchParams(window.location.search).get('recording')).toBe('cmr');
    app.unmount();
    renderApp({ listOffers: async () => listings, market });
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(asked.at(-1)?.recording_type).toBe('cmr');
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    await waitFor(() => expect(visibleNames()).toHaveLength(2));
  }, 15000);

  it("says when a drive's prices could not be loaded", async () => {
    const user = userEvent.setup();
    renderApp({ prices: async () => { throw new Error('Unable to save or load listings (503).'); } });
    await user.click(await screen.findByTitle('Small drive'));
    const details = within(screen.getByRole('dialog', { name: '18 TB drive' }));
    expect(await details.findByRole('alert')).toHaveTextContent('Unable to save or load listings (503).');
    expect(details.queryByText('Loading prices…')).not.toBeInTheDocument();
  });

  it('shows the listings a page at a time, and a change of order starts again from the first page', async () => {
    const user = userEvent.setup();
    const drives = Array.from({ length: 60 }, (_, index) => makeOffer(`Drive ${String(index + 1).padStart(3, '0')}`, {},
      { total_cents: 10000 + index, price_per_tb: (10 + index / 100).toFixed(2) }));
    renderApp({ listOffers: async () => drives });
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
    const drives = Array.from({ length: 60 }, (_, index) => makeOffer(`Drive ${String(index + 1).padStart(3, '0')}`, {},
      { total_cents: 10000 + index, price_per_tb: (10 + index / 100).toFixed(2) }));
    renderApp({ listOffers: async () => drives }, '/', storage);
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
    const listing = makeOffer('History drive', { observations: historyPrices, latest: historyPrices[1] });
    renderApp({ listOffers: async () => [listing], reviewItems: async () => [makeReviewItem('waiting')] });
    await user.click(await screen.findByTitle('History drive'));
    const details = within(screen.getByRole('dialog', { name: '18 TB drive' }));
    expect(details.getByRole('button', { name: 'Record price' })).toBeVisible();
    expect(details.queryByRole('button', { name: /More actions/ })).not.toBeInTheDocument();
    expect(details.queryByRole('button', { name: 'Edit specifications' })).not.toBeInTheDocument();
    await user.click(details.getByRole('button', { name: 'Price history (2)' }));
    expect(details.queryByRole('button', { name: 'Delete price' })).not.toBeInTheDocument();
    expect(within(details.getByRole('table', { name: 'Price history' })).getAllByRole('columnheader').map(header => header.textContent))
      .toEqual(['Store', 'Checked', 'Item', 'Shipping & fees', 'Total', 'Notes']);
    expect(screen.queryByRole('button', { name: /Review queue/ })).not.toBeInTheDocument();
  });
  it("charts the lowest item price at any store selling a drive's condition, with the server's figures, one store's own price when chosen, over a period of its own", async () => {
    const user = userEvent.setup();
    const ago = (days: number) => new Date(checkedAt.getTime() - days * 86_400_000).toISOString();
    const price = (id: string, daysAgo: number, item: number, shipping = 0): Observation =>
      ({ ...makeOffer(id).latest, id, observed_at: ago(daysAgo), entered_at: ago(daysAgo), item_price_cents: item, shipping_cents: shipping, total_cents: item + shipping });
    const drive = makeDrive('ST18000NM000J');
    const offer = (id: string, store: string, prices: Observation[]) => makeOffer(id,
      { drive, mpn: drive.mpn, title: 'Exos X18', store, seller: '', observations: prices, last_checked_at: checkedAt.toISOString() }, prices[prices.length - 1]);
    // The lowest at either store: $190 for 50 days, $170 for 30, $180 for the last 10; shipping is not counted.
    const offers = [
      offer('spd', 'serverpartdeals', [price('spd-1', 60, 20000), price('spd-2', 20, 18000, 1000)]),
      offer('ghd', 'goharddrive', [price('ghd-1', 100, 19000), price('ghd-2', 40, 17000), price('ghd-3', 10, 18500)]),
    ];
    const ranges = {
      30: { today: 18000, low: 17000, high: 18000, average: 17333, days: 30 },
      90: { today: 18000, low: 17000, high: 19000, average: 18222, days: 90 },
    };
    const priceRanges = vi.fn<DisktrackerApi['priceRanges']>(async (_id, days) => ({ new: ranges[days as 30 | 90] }));
    renderApp({ listOffers: async () => offers, priceRanges });
    await user.click(await screen.findByTitle('Exos X18'));
    const region = await screen.findByRole('region', { name: 'Price trend' });
    const trend = within(region);
    const lines = () => [...region.querySelectorAll('.recharts-line-curve')].filter(line => line.getAttribute('d'));
    // Three figures to scan, each with a few words under it, in place of sentences.
    const figures = () => trend.getAllByRole('definition').map(figure => figure.textContent);
    const lowDay = new Date(ago(40)).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    await waitFor(() => expect(trend.getAllByRole('term').map(term => term.textContent)).toEqual(['Today', 'Low', 'Average']));
    expect(figures()).toEqual(['$180.00' + '$10.00 above low', '$170.00' + `GoHardDrive, ${lowDay}`, '$182.22' + 'over 90 days']);
    // One line, the lowest at any store, until a store is chosen to set against it.
    await waitFor(() => expect(lines()).toHaveLength(1));
    const compare = trend.getByRole('combobox', { name: 'Compare a store' });
    expect(within(compare).getAllByRole('option').map(option => option.textContent)).toEqual(['No store', 'ServerPartDeals, $180.00', 'GoHardDrive, $185.00']);
    await user.selectOptions(compare, 'GoHardDrive, $185.00');
    await waitFor(() => expect(lines()).toHaveLength(2));
    // The panel looks back over a period of its own, starting from the table's, and asks the server for it.
    expect(trend.getByRole('button', { name: '90 days' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(trend.getByRole('button', { name: '30 days' }));
    expect(priceRanges).toHaveBeenLastCalledWith(drive.id, 30, 7);
    await waitFor(() => expect(figures()).toEqual(['$180.00' + '$10.00 above low', '$170.00' + `GoHardDrive, ${lowDay}`, '$173.33' + 'over 30 days']));
    expect(screen.getByRole('combobox', { name: 'Days the range looks back over', hidden: true })).toHaveValue('90');
  });

  it('lists one offer row per seller and marks the lowest price, with no separate best-price line', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const fromServerPartDeals = makeOffer('from-serverpartdeals', { drive, title: 'Seagate Exos X20', seller: 'ServerPartDeals' },
      { total_cents: 49900, price_per_tb: '27.72' });
    const fromEbay = makeOffer('from-ebay', { drive, title: 'Seagate Exos X20', seller: 'eBay - drivedeals' },
      { total_cents: 48700, price_per_tb: '27.06' });
    renderApp({ listOffers: async () => [fromServerPartDeals, fromEbay] });
    await user.click(await screen.findByTitle('Seagate Exos X20'));
    const detail = within(screen.getByRole('dialog', { name: '18 TB drive' }));
    expect(detail.queryByText(/Best price/)).not.toBeInTheDocument();
    expect(detail.queryByLabelText('Price measure')).not.toBeInTheDocument();
    const offers = within(detail.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    expect(within(offers[0]).getByText('Lowest')).toBeVisible();
    expect(within(offers[1]).queryByText('Lowest')).not.toBeInTheDocument();
    expect(detail.getByRole('region', { name: 'Price trend' })).toBeVisible();
    expect(offers.map(row => within(row).getAllByRole('cell')[0].querySelector('strong')?.textContent)).toEqual(['eBay - drivedeals', 'ServerPartDeals']);
    expect(within(offers[0]).getByText('$487.00')).toBeVisible();
    expect(detail.getAllByRole('button', { name: 'Record price' })).toHaveLength(2);
    expect(within(offers[0]).getByRole('button', { name: 'Record price' })).toBeVisible();
  });

  it("shows each seller's price change in its offer row, with no separate per-seller price section", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const tracked = makeOffer('tracked', { drive, title: 'Seagate Exos X20', seller: 'GoHardDrive', observations: historyPrices, latest: historyPrices[1] });
    const other = makeOffer('other', { drive, title: 'Seagate Exos X20', seller: 'ServerPartDeals' }, { total_cents: 99999, price_per_tb: '99.99' });
    renderApp({ listOffers: async () => [tracked, other] });
    await user.click(await screen.findByTitle('Seagate Exos X20'));
    const detail = within(screen.getByRole('dialog', { name: '18 TB drive' }));
    const offers = within(detail.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    expect(within(offers[0]).getByText('▼ $15.00 (6.5%)')).toBeVisible();
    expect(detail.queryByRole('region', { name: 'Current price' })).not.toBeInTheDocument();
  });

  it("shows each offer's total, $/TB, and check time under its condition", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const unknownShipping = makeOffer('spd', { drive, title: 'Seagate Exos X18', seller: 'ServerPartDeals', condition: 'manufacturer_recertified' },
      { item_price_cents: 36999, shipping_cents: 0, total_cents: 36999, price_per_tb: '20.56' });
    const priced = makeOffer('newegg', { drive, title: 'Seagate Exos X18', seller: 'Newegg', condition: 'new' },
      { item_price_cents: 52999, total_cents: 52999, price_per_tb: '29.44' });
    renderApp({ listOffers: async () => [unknownShipping, priced] });
    await user.click(await screen.findByTitle('Seagate Exos X18'));
    const rowFor = (seller: string) => within(within(screen.getByRole('table', { name: 'Offers' })).getByText(seller).closest('tr')!);
    // It opens on the condition of the row chosen: the recertified offer, the cheaper per TB.
    expect(screen.getByRole('radio', { name: /^Recertified/ })).toBeChecked();
    expect(rowFor('ServerPartDeals').getByText('$369.99')).toBeVisible();
    await user.click(screen.getByRole('radio', { name: /^New/ }));
    expect(rowFor('Newegg').getByText('$29.44')).toBeVisible();
    expect(rowFor('Newegg').getByText('<1h ago')).toHaveAttribute('datetime', checkedAt.toISOString());
  });

  it('names each offer by its store, or by the store for Other', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const direct = makeOffer('direct', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', store: 'serverpartdeals', seller: '' },
      { total_cents: 36999, price_per_tb: '20.56' });
    const marketplace = makeOffer('marketplace', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', store: 'other', seller: 'Beach Audio' },
      { total_cents: 88453, price_per_tb: '49.14' });
    const range = { today: 18000, low: 18000, high: 18000, average: 18000, days: 0 };
    renderApp({ listOffers: async () => [direct, marketplace], priceRanges: async () => ({ new: range }) });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getByText('ServerPartDeals +1 more')).toBeVisible();
    await user.click(table.getByTitle('Seagate Exos X18'));
    const detail = within(screen.getByRole('dialog', { name: '18 TB drive' }));
    const offers = within(await detail.findByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    expect(offers.map(row => within(row).getAllByRole('cell')[0].querySelector('strong')?.textContent)).toEqual(['ServerPartDeals', 'Beach Audio']);
    const compare = within(detail.getByRole('region', { name: 'Price trend' })).getByRole('combobox', { name: 'Compare a store' });
    expect(within(compare).getAllByRole('option').map(option => option.textContent)).toEqual(['No store', 'ServerPartDeals, $180.00', 'Beach Audio, $180.00']);
    await user.click(detail.getByRole('button', { name: 'Price history (2)' }));
    expect(within(detail.getByRole('table', { name: 'Price history' })).getByText('Beach Audio')).toBeVisible();
  });

  it("asks for a page of drives with the filters, and for a drive and its prices by the drive when it is opened", async () => {
    window.history.replaceState(null, '', '/?condition=new&sort=total-desc&days=30');
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const offers = [
      makeOffer('spd', { drive, mpn: drive.mpn, title: 'Exos X20', store: 'serverpartdeals', seller: '' }),
      makeOffer('ghd', { drive, mpn: drive.mpn, title: 'Exos X20', store: 'goharddrive', seller: '' }),
      makeOffer('Unrelated drive', { observations: historyPrices, latest: historyPrices[1] }),
    ];
    const market = vi.fn<DisktrackerApi['market']>(async query => marketPage(rowsOf(offers), {}, query));
    const opened = vi.fn<DisktrackerApi['driveOffers']>(async () => offers.slice(0, 2));
    const prices = vi.fn<DisktrackerApi['prices']>(async request => pricesOf(offers.slice(0, 2), request));
    renderApp({ listOffers: async () => offers, market, driveOffers: opened, prices });
    await user.click(await screen.findByTitle('Exos X20'));
    expect(market).toHaveBeenCalledWith({ condition: ['new'], recent_days: 7, sort: 'total-desc', range_days: 30, limit: 50, offset: 0 });
    // Nothing is asked of a drive's prices until it is opened, and then by the drive, over the period shown.
    expect(opened).toHaveBeenCalledWith(drive.id);
    expect(prices).toHaveBeenCalledWith({ driveId: drive.id, since: new Date(checkedAt.getTime() - 30 * 86_400_000).toISOString(), limit: 500, offset: 0 });
    expect(await screen.findByRole('button', { name: 'Price history (2)' })).toBeVisible();
  });

  it('chooses conditions with buttons above the list, and names on each row the other conditions the drive is sold in', async () => {
    window.history.replaceState(null, '', '/?stock=all');
    const user = userEvent.setup();
    const ultrastar = makeDrive('WUH721818ALE604'), exos = makeDrive('ST18000NM000J');
    const offer = (id: string, drive: typeof exos, title: string, store: string, condition: Condition, total: number, price = {}) => makeOffer(id,
      { drive, mpn: drive.mpn, title, store, seller: '', condition }, { item_price_cents: total, total_cents: total, price_per_tb: (total / 1800).toFixed(2), ...price });
    const uNew = offer('u-new', ultrastar, 'Ultrastar HC550', 'serverpartdeals', 'new', 45000, { in_stock: false });
    const uRecertified = offer('u-recertified', ultrastar, 'Ultrastar HC550', 'serverpartdeals', 'manufacturer_recertified', 48900);
    const uRefurbished = offer('u-refurbished', ultrastar, 'Ultrastar HC550', 'goharddrive', 'refurbished', 47000);
    const eNew = offer('e-new', exos, 'Exos X18', 'serverpartdeals', 'new', 50000);
    const conditions_ = [{ value: 'new' as const, drives: 2 }, { value: 'manufacturer_recertified' as const, drives: 1 }, { value: 'refurbished' as const, drives: 1 }];
    // What the server answers for each choice of conditions: the drives, each shown by its cheapest offer in them.
    const { asked, market } = server(query => {
      const chosen = query.condition ?? [];
      const rows = chosen.length === 0 ? rowsOf([uRefurbished, uNew, uRecertified, eNew])
        : chosen.includes('refurbished') ? rowsOf([uRefurbished, uNew, eNew])
          : rowsOf([eNew, uNew]);
      return marketPage(rows, { filter_options: { ...noOptions(), conditions: conditions_ } });
    });
    renderApp({ listOffers: async () => [uNew, uRecertified, uRefurbished, eNew], market });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    const conditions = within(screen.getByRole('group', { name: 'Condition' }));
    const pressed = () => conditions.getAllByRole('button').filter(button => button.getAttribute('aria-pressed') === 'true').map(button => button.textContent);
    // The conditions the server says there are offers in, each with how many drives are sold in it.
    expect(conditions.getAllByRole('button').map(button => button.textContent)).toEqual(['New (2)', 'Recertified (1)', 'Refurbished (1)']);
    expect(pressed()).toEqual([]);
    expect(screen.getByText('Lowest price per drive. $/TB and totals include shipping, before tax.')).toBeVisible();
    const row = (name: string) => within(table.getByTitle(name).closest('tr')!);
    const others = (name: string) => row(name).getAllByRole('button').slice(1).map(button => button.textContent);
    expect(visibleNames()).toEqual(['Ultrastar HC550', 'Exos X18']);
    expect(row('Ultrastar HC550').getByText('$470.00')).toBeVisible();
    expect(others('Ultrastar HC550')).toEqual(['New Out of stock', 'Recertified $489.00']);
    expect(others('Exos X18')).toEqual([]);
    // Another condition named on a row opens the drive on it.
    await user.click(row('Ultrastar HC550').getByRole('button', { name: 'Recertified $489.00' }));
    expect(within(screen.getByRole('dialog', { name: '18 TB drive' })).getByRole('radio', { name: /^Recertified/ })).toBeChecked();
    await user.keyboard('{Escape}');

    await user.click(conditions.getByRole('button', { name: 'New (2)' }));
    expect(asked.at(-1)?.condition).toEqual(['new']);
    expect(pressed()).toEqual(['New (2)']);
    expect(new URLSearchParams(window.location.search).getAll('condition')).toEqual(['new']);
    expect(screen.getByText('Lowest price per drive, New. $/TB and totals include shipping, before tax.')).toBeVisible();
    await waitFor(() => expect(visibleNames()).toEqual(['Exos X18', 'Ultrastar HC550']));
    expect(row('Ultrastar HC550').getByText('$450.00')).toBeVisible();
    expect(row('Ultrastar HC550').getByText('Out of stock')).toBeVisible();
    expect(others('Ultrastar HC550')).toEqual([]);
    await user.click(conditions.getByRole('button', { name: 'Refurbished (1)' }));
    expect(asked.at(-1)?.condition).toEqual(['new', 'refurbished']);
    expect(screen.getByText('Lowest price per drive, New or Refurbished. $/TB and totals include shipping, before tax.')).toBeVisible();
    await waitFor(() => expect(row('Ultrastar HC550').getByText('$470.00')).toBeVisible());
    expect(others('Ultrastar HC550')).toEqual(['New Out of stock']);
    // The buttons already show what is chosen, so they are not repeated as chips; Clear filters lets go of them.
    expect(screen.getByLabelText('Active filters')).toHaveTextContent(/^Including out of stock ×$/);
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(pressed()).toEqual([]);
    expect(window.location.search).toBe('');
  }, 20000);

  it('keeps each condition of a drive apart: its own offers, lowest price, trend and history, switched between at the top', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('WUH721818ALE604');
    const offer = (id: string, store: string, condition: Condition, total: number, fields = {}, price = {}) => makeOffer(id,
      { drive, mpn: drive.mpn, title: 'Ultrastar HC550', store, seller: '', condition, ...fields },
      { item_price_cents: total, total_cents: total, price_per_tb: (total / 1800).toFixed(2), ...price });
    const earlier = { ...historyPrices[0], id: 'earlier', observed_at: '2026-09-14T12:00:00Z', item_price_cents: 50000, total_cents: 50000 };
    const recertified = offer('recertified', 'serverpartdeals', 'manufacturer_recertified', 48900);
    const listings = [
      offer('new', 'serverpartdeals', 'new', 45000, {}, { in_stock: false }),
      { ...recertified, observations: [earlier, recertified.latest] },
      offer('refurbished-spd', 'serverpartdeals', 'refurbished', 48900),
      offer('refurbished-ghd', 'goharddrive', 'refurbished', 47000),
    ];
    const [fresh, olderRecertified, refurbishedSpd, refurbishedGhd] = listings;
    const ranges = {
      new: null,
      manufacturer_recertified: { today: 48900, low: 48900, high: 50000, average: 49450, days: 8 },
      refurbished: { today: 47000, low: 47000, high: 48900, average: 47000, days: 0 },
    };
    renderApp({
      listOffers: async () => listings,
      // Shown by its cheapest offer in stock, or by its recertified one when that is the condition asked for.
      market: async query => marketPage(rowsOf(query.condition?.includes('manufacturer_recertified')
        ? [olderRecertified] : [refurbishedGhd, fresh, olderRecertified, refurbishedSpd]), {
        filter_options: { ...noOptions(), conditions: [{ value: 'manufacturer_recertified', drives: 1 }] },
      }, query),
      priceRanges: async () => ranges,
    });
    // Four offers from two stores: the row counts stores, as it says.
    expect(await screen.findByText('GoHardDrive +1 more')).toBeVisible();
    await user.click(await screen.findByTitle('Ultrastar HC550'));
    const panel = within(screen.getByRole('dialog', { name: '18 TB drive' }));
    // One store sells three of the four offers: it is stores that are counted.
    expect(panel.getByText('WUH721818ALE604, 2 stores')).toBeVisible();
    const conditions = within(panel.getByRole('radiogroup', { name: 'Condition' }));
    // Each choice says what that condition costs now, so they can be compared without switching.
    expect(conditions.getAllByRole('radio').map(radio => (radio as HTMLInputElement).labels?.[0].textContent))
      .toEqual(['New' + 'Out of stock', 'Recertified' + '$489.00', 'Refurbished' + 'from $470.00']);
    // It opens on the condition of the row chosen: the cheapest in stock, a refurbished one.
    expect(conditions.getByRole('radio', { name: /^Refurbished/ })).toBeChecked();
    const offers = () => within(panel.getByRole('table', { name: 'Offers' }));
    const stores = () => offers().getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].querySelector('strong')?.textContent);
    expect(offers().getAllByRole('columnheader').map(header => header.textContent)).toEqual(['Store', '$/TB', 'Total', 'Checked', 'Actions']);
    expect(stores()).toEqual(['GoHardDrive', 'ServerPartDeals']);
    expect(within(offers().getAllByRole('row')[1]).getByText('Lowest')).toBeVisible();
    const trend = within(panel.getByRole('region', { name: 'Price trend' }));
    // Within a condition only the store differs, so the store names what can be set against the lowest.
    expect(within(trend.getByRole('combobox', { name: 'Compare a store' })).getAllByRole('option').map(option => option.textContent))
      .toEqual(['No store', 'GoHardDrive, $470.00', 'ServerPartDeals, $489.00']);
    expect(panel.getByRole('button', { name: 'Price history (2)' })).toBeVisible();

    await user.click(conditions.getByRole('radio', { name: /^Recertified/ }));
    expect(stores()).toEqual(['ServerPartDeals']);
    expect(within(offers().getAllByRole('row')[1]).getByText('Lowest')).toBeVisible();
    // Down from $500.00 eight days ago, and one store alone.
    expect(trend.getAllByRole('definition')[0]).toHaveTextContent('$489.00' + 'At its lowest');
    expect(trend.queryByRole('combobox', { name: 'Compare a store' })).not.toBeInTheDocument();
    await user.click(panel.getByRole('button', { name: 'Price history (2)' }));
    const history = within(panel.getByRole('table', { name: 'Price history' }));
    expect(history.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent)).toEqual(['ServerPartDeals', 'ServerPartDeals']);

    // A condition that is sold out has no lowest price to claim.
    await user.click(conditions.getByRole('radio', { name: /^New/ }));
    expect(stores()).toEqual(['ServerPartDeals']);
    expect(offers().getByText('Out of stock')).toBeVisible();
    expect(offers().queryByText('Lowest')).not.toBeInTheDocument();
    expect(trend.getByText('No prices in the last 90 days')).toBeVisible();
    expect(panel.getByRole('button', { name: 'Price history (1)' })).toBeVisible();

    // Filtered to one condition, a row opens on that condition.
    await user.keyboard('{Escape}');
    await user.click(within(screen.getByRole('group', { name: 'Condition' })).getByRole('button', { name: /^Recertified/ }));
    await user.click(screen.getByTitle('Ultrastar HC550'));
    expect(screen.getByRole('radio', { name: /^Recertified/ })).toBeChecked();
  }, 20000);

  it('records a price for a new offer of a drive made by its MPN, at its store, seller, and condition, keeping filters when it is hidden', async () => {
    window.history.replaceState(null, '', '/?q=Small');
    const user = userEvent.setup();
    let listings = [...shoppingListings];
    const made = makeDrive('ST20000NM007D', { capacity_gb: 20000 });
    const createDrive = vi.fn<DisktrackerApi['createDrive']>(async () => made);
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async input => {
      const saved = makeOffer('saved', { drive: made, title: input.title ?? made.mpn, mpn: made.mpn, store: input.store ?? 'other',
        seller: input.seller, condition: input.condition ?? 'new', capacity_gb: made.capacity_gb, url: input.url ?? null });
      listings = [...listings, saved];
      return recordedOn(saved, saved.latest.id);
    });
    // Searched for Small, the server lists only the small drive; asked for the saved one under the same filters, nothing.
    const { asked, market } = server(query => marketPage(query.drive_id ? [] : rowsOf([shoppingListings[0]])));
    renderApp({ listOffers: async () => listings, createDrive, recordPrice, market });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    const dialog = screen.getByRole('dialog', { name: 'Record price' });
    const form = within(dialog);
    const shownFields = () => [...dialog.querySelectorAll('[aria-label]')]
      .filter(field => ['INPUT', 'SELECT', 'TEXTAREA'].includes(field.tagName) && !field.closest('details:not([open])'))
      .map(field => field.getAttribute('aria-label'));
    // The store and its page come first: they are what the copied text is from, and what a later recheck opens.
    expect(shownFields()).toEqual(['Paste from store page', 'Store', 'Store page URL', 'MPN', 'Capacity', 'Condition', 'Item price (USD)', 'Shipping & fees (USD)']);
    expect(within(form.getByLabelText('Condition', { exact: true })).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Choose condition', 'New', 'Recertified', 'Refurbished', 'Used']);
    expect(within(form.getByLabelText('Capacity', { exact: true })).getAllByRole('option').map(option => option.textContent))
      .toContain('20 TB');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    expect(within(form.getByLabelText('Store', { exact: true })).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Choose store', 'ServerPartDeals', 'GoHardDrive', 'Western Digital', 'Other']);
    await user.click(form.getByRole('button', { name: 'Save price' }));
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
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(createDrive).toHaveBeenCalledWith({ mpn: 'ST20000NM007D', capacity_gb: 20000 });
    expect(recordPrice).toHaveBeenCalledWith({
      drive_id: 'drive-ST20000NM007D', store: 'other', seller: 'Beach Audio', condition: 'refurbished',
      title: 'New drive', url: null, item_price_cents: 25000, shipping_cents: 0,
      in_stock: true, observed_at: null, notes: '',
    }, 'save-key');
    expect(await screen.findByText('It is hidden by your filters.')).toBeVisible();
    expect(asked.find(query => query.drive_id)).toMatchObject({ q: 'Small', drive_id: 'drive-ST20000NM007D', limit: 1 });
    expect(screen.getByLabelText('Search drives')).toHaveValue('Small');
    expect(visibleNames()).toEqual(['Small drive']);
    await user.click(screen.getByRole('button', { name: 'Show drive' }));
    const details = within(screen.getByRole('dialog', { name: '20 TB drive' }));
    expect(details.getByRole('table', { name: 'Offers' })).toBeVisible();
    expect(new URLSearchParams(window.location.search).get('q')).toBe('Small');
  });

  it('suggests the MPNs of drives already known while one is typed', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J', { aliases: ['0HNHWC'] });
    const listings = [
      makeOffer('Exos X18', { drive, mpn: drive.mpn, capacity_gb: 18000 }),
      makeOffer('Exos X20', { drive: makeDrive('ST20000NM007D'), mpn: 'ST20000NM007D', capacity_gb: 20000 }),
    ];
    // The drives the server finds by the MPN typed so far: here, only the Exos X18; and the one that goes by
    // the MPN exactly, if any does.
    const findDrives = vi.fn<DisktrackerApi['findDrives']>(async query => foundPage(query.mpn
      ? rowsOf(listings).filter(row => row.drive.mpn === query.mpn!.toUpperCase()) : rowsOf(listings.slice(0, 1)), query));
    renderApp({ listOffers: async () => listings, findDrives });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    await user.type(form.getByLabelText('MPN', { exact: true }), 'st18');
    // Asked for once the MPN stops changing, not at every letter.
    // Suggested by words, and looked up exactly, once typing pauses.
    await waitFor(() => expect(findDrives).toHaveBeenCalledWith({ q: 'st18', limit: 8, offset: 0 }));
    expect(findDrives.mock.calls).toEqual([[{ q: 'st18', limit: 8, offset: 0 }], [{ mpn: 'st18', limit: 1, offset: 0 }]]);
    await waitFor(() => expect(within(screen.getByRole('listbox')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['ST18000NM000J · Exos X18']));
    // Like but not the same: no capacity is taken from it.
    expect(form.getByLabelText('Capacity', { exact: true })).toBeVisible();
    await user.click(screen.getByRole('option', { name: 'ST18000NM000J · Exos X18' }));
    expect(form.getByLabelText('MPN', { exact: true })).toHaveValue('ST18000NM000J');
    expect(await form.findByText('18 TB, as recorded for this drive')).toBeVisible();
  });

  it('starts each new price with the store and condition last used, even after a reload', async () => {
    const user = userEvent.setup();
    const storage = memoryStorage();
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn({ id: 'saved' }));
    const app = renderApp({ recordPrice }, '/', storage);
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    let form = within(screen.getByRole('dialog', { name: 'Record price' }));
    expect(form.getByLabelText('Store', { exact: true })).toHaveValue('');
    await user.type(form.getByLabelText('MPN', { exact: true }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'refurbished');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Record price' })).not.toBeInTheDocument());
    app.unmount();
    renderApp({ recordPrice }, '/', storage);
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    form = within(screen.getByRole('dialog', { name: 'Record price' }));
    expect(form.getByLabelText('Store', { exact: true })).toHaveValue('goharddrive');
    expect(form.getByLabelText('Condition', { exact: true })).toHaveValue('refurbished');
  }, 15000);

  it('saves a price with Enter from any field', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn({ id: 'saved' }));
    renderApp({ recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    await user.type(form.getByLabelText('MPN', { exact: true }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'new');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250{Enter}');
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({ drive_id: 'drive-ST20000NM007D', item_price_cents: 25000 }), 'save-key');
  }, 15000);

  it('saves and starts another new price, keeping the store and condition', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn({ id: 'saved' }));
    renderApp({ recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    let form = within(screen.getByRole('dialog', { name: 'Record price' }));
    await user.type(form.getByLabelText('MPN', { exact: true }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'new');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250');
    await user.click(form.getByRole('button', { name: 'Save and add another' }));
    expect(recordPrice).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(within(screen.getByRole('dialog', { name: 'Record price' })).getByLabelText('MPN', { exact: true })).toHaveValue(''));
    form = within(screen.getByRole('dialog', { name: 'Record price' }));
    expect(form.getByLabelText('Item price (USD)', { exact: true })).toHaveValue('');
    expect(form.getByLabelText('Store', { exact: true })).toHaveValue('goharddrive');
    expect(form.getByLabelText('Condition', { exact: true })).toHaveValue('new');
    expect(form.getByRole('status')).toHaveTextContent('Saved ST20000NM007D. Add the next offer.');
  }, 15000);

  it('fills a new price from pasted listing text, for checking before it is saved', async () => {
    const user = userEvent.setup();
    const pasted = 'Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive\n$219.99\nIn stock';
    const readListing = vi.fn<DisktrackerApi['readListing']>(async () => ({
      title: 'Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive', mpn: 'ST18000NM000J',
      capacity_gb: 18000, condition: 'refurbished', brand: 'Seagate', item_price_cents: 21999,
    }));
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn({ id: 'saved' }));
    renderApp({ readListing, recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
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
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({
      drive_id: 'drive-ST18000NM000J', condition: 'refurbished', item_price_cents: 21999,
      title: 'Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive',
    }), 'save-key');
  }, 15000);

  it('says what pasted text did not give, and moves to the first field left to fill', async () => {
    const user = userEvent.setup();
    const readListing = vi.fn<DisktrackerApi['readListing']>(async () => ({
      title: 'Exos X18 hard drive', mpn: 'ST18000NM000J', capacity_gb: null, condition: null, brand: null, item_price_cents: 21999,
    }));
    renderApp({ readListing });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    await user.type(form.getByRole('textbox', { name: 'Paste from store page' }), 'Exos X18 hard drive $219.99');
    await user.click(form.getByRole('button', { name: 'Fill in' }));
    expect(await form.findByRole('status')).toHaveTextContent('Filled in: title, MPN, price. Not found: capacity, condition.');
    expect(form.getByLabelText('Capacity', { exact: true })).toHaveFocus();
    // Nothing recognisable is said too, rather than leaving the form looking untouched.
    readListing.mockResolvedValueOnce({ title: null, mpn: null, capacity_gb: null, condition: null, brand: null, item_price_cents: null });
    await user.click(form.getByRole('button', { name: 'Fill in' }));
    await waitFor(() => expect(form.getByRole('status')).toHaveTextContent('Nothing could be read from that text. Not found: title, MPN, capacity, condition, price.'));
  }, 15000);

  it('records a later price for an existing offer from its row, naming that offer', async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const offer = makeOffer('offer', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', store: 'serverpartdeals', seller: '',
      condition: 'manufacturer_recertified', url: 'https://example.com/x18', capacity_gb: 18000 });
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn(offer));
    renderApp({ listOffers: async () => [offer], recordPrice });
    await user.click(await screen.findByTitle('Seagate Exos X18'));
    const offers = within(screen.getByRole('table', { name: 'Offers' }));
    const [row] = offers.getAllByRole('row').slice(1);
    // The price is typed in the panel itself, under the offer: no second window opens over it.
    expect(offers.queryByRole('textbox')).not.toBeInTheDocument();
    await user.click(within(row).getByRole('button', { name: 'Record price' }));
    expect(within(row).getByRole('button', { name: 'Record price' })).toHaveAttribute('aria-expanded', 'true');
    expect(offers.getByRole('link', { name: 'View at store' })).toHaveAttribute('href', 'https://example.com/x18');
    await user.type(offers.getByRole('textbox', { name: 'New price for Seagate Exos X18' }), '170{Enter}');
    expect(recordPrice).toHaveBeenCalledWith({
      offer_id: offer.id, item_price_cents: 17000, shipping_cents: 0, in_stock: true, observed_at: null, notes: '',
    }, 'save-key');
    expect(await screen.findByRole('status')).toHaveTextContent('Recorded $170.00 for Seagate Exos X18.');
    expect(screen.queryByRole('dialog', { name: 'Record price' })).not.toBeInTheDocument();
    await waitFor(() => expect(offers.queryByRole('textbox')).not.toBeInTheDocument());
  });

  it('opens the full form from an offer for a price with its own shipping, date or notes', async () => {
    const user = userEvent.setup();
    const offer = makeOffer('offer', { mpn: 'ST18000NM000J', title: 'Seagate Exos X18', store: 'serverpartdeals', seller: '', condition: 'manufacturer_recertified' });
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn(offer));
    renderApp({ listOffers: async () => [offer], recordPrice });
    await user.click(await screen.findByTitle('Seagate Exos X18'));
    await user.click(within(screen.getByRole('table', { name: 'Offers' })).getByRole('button', { name: 'Record price' }));
    await user.click(screen.getByRole('button', { name: 'More options' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    expect(form.getByText('Seagate Exos X18 · ServerPartDeals · Recertified')).toBeVisible();
    expect(form.queryByRole('textbox', { name: 'MPN' })).not.toBeInTheDocument();
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '170');
    await user.type(form.getByLabelText('Shipping & fees (USD)', { exact: true }), '9.99');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({ item_price_cents: 17000, shipping_cents: 999 }), 'save-key');
  });

  it("reuses a known drive's capacity when recording a price for its MPN", async () => {
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const known = makeOffer('known', { drive, mpn: drive.mpn, title: 'Seagate Exos X18', capacity_gb: 18000 });
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn(known));
    renderApp({ listOffers: async () => [known], recordPrice });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(within(screen.getByRole('banner')).getByRole('button', { name: 'Record price' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST18000NM000J');
    expect(await form.findByText('18 TB, as recorded for this drive')).toBeVisible();
    expect(form.queryByLabelText('Capacity', { exact: true })).not.toBeInTheDocument();
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    expect(form.queryByRole('textbox', { name: 'Seller name' })).not.toBeInTheDocument();
    await user.click(form.getByText('More details'));
    await user.type(form.getByRole('textbox', { name: 'Offer title' }), 'Exos X18 from GoHardDrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'new');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '529.99');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    // Of the drive already recorded: none is made.
    expect(recordPrice).toHaveBeenCalledWith({
      drive_id: drive.id, store: 'goharddrive', seller: '', condition: 'new', title: 'Exos X18 from GoHardDrive',
      url: null, item_price_cents: 52999, shipping_cents: 0, in_stock: true,
      observed_at: null, notes: '',
    }, 'save-key');
  }, 15000);

  it('shows plain prices with no stock status or unknown amounts anywhere', async () => {
    const user = userEvent.setup();
    const offer = makeOffer('Plain drive', {}, { item_price_cents: 18000, shipping_cents: 1250, total_cents: 19250, price_per_tb: '10.69' });
    renderApp({ listOffers: async () => [offer] });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.queryByText(/In stock|Unknown/)).not.toBeInTheDocument();
    expect(table.getByText('$192.50')).toBeVisible();
    expect(screen.queryByLabelText('Availability')).not.toBeInTheDocument();
    await user.click(table.getByTitle('Plain drive'));
    await user.click(screen.getByRole('button', { name: 'Price history (1)' }));
    const history = within(screen.getByRole('table', { name: 'Price history' }));
    expect(history.getAllByRole('columnheader').map(header => header.textContent))
      .toEqual(['Store', 'Checked', 'Item', 'Shipping & fees', 'Total', 'Notes']);
    expect(history.getByText('$12.50')).toBeVisible();
  });

  it('never marks a sold-out offer as lowest, flags shipping not included, and shows when each offer was last checked', async () => {
    // Sold-out offers are left out unless asked for; this is about how they show.
    window.history.replaceState(null, '', '/?stock=all');
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM000J');
    const soldOut = makeOffer('sold', { drive, title: 'Seagate Exos X18', seller: 'Cheap shop' },
      { item_price_cents: 30000, total_cents: 30000, price_per_tb: '16.67', in_stock: false });
    const stocked = makeOffer('stocked', { drive, title: 'Seagate Exos X18', seller: 'Pricier shop', last_checked_at: '2026-09-22T11:00:00Z' },
      { item_price_cents: 40000, shipping_cents: null, shipping_known: false, total_cents: 40000, price_per_tb: '22.22',
        observed_at: '2026-09-20T12:00:00Z' });
    // The server shows the drive by its offer in stock.
    renderApp({ listOffers: async () => [soldOut, stocked], market: async () => marketPage(rowsOf([stocked, soldOut])) });
    const table = within(await screen.findByRole('table', { name: 'Drive prices' }));
    expect(table.getByText('Pricier shop +1 more')).toBeVisible();
    await user.click(table.getByTitle('Seagate Exos X18'));
    const offers = within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
    const rowFor = (seller: string) => within(offers.find(row => within(row).queryByText(seller))!);
    expect(rowFor('Cheap shop').getByText('Out of stock')).toBeVisible();
    expect(rowFor('Cheap shop').queryByText('Lowest')).not.toBeInTheDocument();
    expect(rowFor('Pricier shop').getByText('Lowest')).toBeVisible();
    expect(rowFor('Pricier shop').getByText('+ shipping')).toBeVisible();
    expect(rowFor('Pricier shop').getByText('1h ago')).toHaveAttribute('title', new Date('2026-09-22T11:00:00Z').toLocaleString());
  });

  it('records that an existing offer is out of stock without needing a new price', async () => {
    const user = userEvent.setup();
    const offer = makeOffer('Exos X18', { mpn: 'ST18000NM000J' });
    const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn(offer));
    renderApp({ listOffers: async () => [offer], recordPrice });
    await user.click(await screen.findByTitle('Exos X18'));
    const offers = within(screen.getByRole('table', { name: 'Offers' }));
    await user.click(offers.getByRole('button', { name: 'Record price' }));
    await user.click(offers.getByRole('button', { name: 'Out of stock' }));
    expect(recordPrice).toHaveBeenCalledWith({
      offer_id: offer.id, item_price_cents: null, shipping_cents: 0, in_stock: false, observed_at: null, notes: '',
    }, 'save-key');
  });

  it('connects filters, sorting, URL state, and Clear filters', async () => {
    const user = userEvent.setup();
    const [small, large, pricey] = shoppingListings;
    const { asked, market } = server(query => marketPage(rowsOf(query.max_total_cents ? [small]
      : query.sort === 'total-asc' ? [small, large, pricey] : [large, small, pricey])));
    const app = renderApp({ market });
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.selectOptions(screen.getByLabelText('Sort by'), 'total-asc');
    expect(asked.at(-1)?.sort).toBe('total-asc');
    await waitFor(() => expect(visibleNames()).toEqual(['Small drive', 'Large drive', 'Pricey drive']));
    await user.type(screen.getByLabelText('Maximum total (USD)'), '180{Enter}');
    expect(asked.at(-1)).toMatchObject({ sort: 'total-asc', max_total_cents: 18000 });
    await waitFor(() => expect(visibleNames()).toEqual(['Small drive']));
    expect(new URLSearchParams(window.location.search).get('maxTotal')).toBe('180');
    app.unmount();
    renderApp({ market });
    await screen.findByRole('table', { name: 'Drive prices' });
    expect(screen.getByLabelText('Maximum total (USD)')).toHaveValue('180');
    expect(screen.getByLabelText('Sort by')).toHaveValue('total-asc');
    expect(asked.at(-1)).toMatchObject({ sort: 'total-asc', max_total_cents: 18000 });
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(new URLSearchParams(window.location.search).has('maxTotal')).toBe(false);
    await user.selectOptions(screen.getByLabelText('Sort by'), 'unit-asc');
    await waitFor(() => expect(visibleNames()).toEqual(['Large drive', 'Small drive', 'Pricey drive']));
  });

  it('explains an empty filtered view and offers an explicit reset', async () => {
    window.history.replaceState(null, '', '/?q=does-not-exist');
    // Nothing matches, though there are drives: the server's options count them.
    const capacities = [{ value: 18000, drives: 3 }];
    renderApp({ market: async query => marketPage(query.q ? [] : rowsOf(shoppingListings), { filter_options: { ...noOptions(), capacities } }) });
    expect(await screen.findByText('No drives match these filters.')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(await screen.findByRole('table', { name: 'Drive prices' })).toBeVisible();
  });

});
