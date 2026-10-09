import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApiValidationError, type CollectorRun, type CollectorStatus, type ConditionRule, type ListingsApi, type Source, type SourceInput, type SourceInspection, type SourceKindDescription, type SourcePreview } from '../../src/api';
import { emptySpecifications } from '../../src/specifications';
import { checkedAt, historyPrices, makeDrive, makeListing, makeSource, makeUnmatched } from '../fixtures/listings';
import { memoryStorage, namesIn, renderApp } from '../fixtures/render-app';

beforeEach(() => { window.history.replaceState(null, '', '/admin'); });
afterEach(() => { cleanup(); window.history.replaceState(null, '', '/'); });

const adminNames = () => namesIn('Drives');
/** Opens the app on one of the admin page's tabs. */
const at = (tab: 'stores' | 'drives') => window.history.replaceState(null, '', `/admin/${tab}`);
const daysAgo = (days: number) => new Date(checkedAt.getTime() - days * 86_400_000).toISOString();

function statValue(region: string, label: string) {
  const term = within(screen.getByRole('region', { name: region })).getByText(label, { selector: 'dt' });
  return term.nextElementSibling?.textContent;
}

const ago = (minutes: number) => new Date(checkedAt.getTime() - minutes * 60_000).toISOString();
/** GoHardDrive two hours into a run, with ServerPartDeals and then Western Digital waiting behind it. */
function collecting(fields: Partial<CollectorStatus> = {}): CollectorStatus {
  return {
    seen_at: ago(0.3), waiting: ['serverpartdeals', 'westerndigital'],
    running: [{ source: 'goharddrive', started_at: ago(125), updated_at: ago(0.3), seen: 412, recorded: 398, queued: 9, ignored: 5, failed: 0 }],
    ...fields,
  };
}

function run(source: string, fields: Partial<CollectorRun> = {}): CollectorRun {
  return {
    source, started_at: '2026-09-22T07:50:00Z', finished_at: '2026-09-22T08:00:00Z', completed: true,
    seen: 70, recorded: 68, queued: 2, ignored: 0, failed: 0, rechecked: 3, recheck_failed: 0, stopped: false, ...fields,
  };
}

/** Three drives: one two stores sell, one only ServerPartDeals sells and has not checked in 10 days,
 * one only a hand-entered store sells. Only the first has specifications. */
function catalogue() {
  const known = makeDrive('ST18000NM003D', { specifications: { ...emptySpecifications(), interface: 'sata' } });
  const stale = makeDrive('WUH721818ALE6L4');
  const manual = makeDrive('WD120EFBX');
  return [
    makeListing('Exos X20', { drive: known, mpn: known.mpn, store: 'serverpartdeals', seller: '' }),
    makeListing('Exos X20 at GoHardDrive', { drive: known, mpn: known.mpn, store: 'goharddrive', seller: '' }, { in_stock: false }),
    makeListing('Ultrastar HC550', { drive: stale, mpn: stale.mpn, store: 'serverpartdeals', seller: '', last_checked_at: daysAgo(10) },
      { observed_at: daysAgo(10), entered_at: daysAgo(10) }),
    makeListing('WD Red Plus', { drive: manual, mpn: manual.mpn, store: 'other', seller: 'Micro Center' }),
  ];
}

describe('Admin page', () => {
  it('is reached from the header and leads back to the listings', async () => {
    window.history.replaceState(null, '', '/');
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('table', { name: 'Drive prices' });
    await user.click(screen.getByRole('link', { name: 'Admin' }));
    expect(await screen.findByRole('heading', { name: 'Admin' })).toBeVisible();
    expect(window.location.pathname).toBe('/admin');
    expect(screen.getByRole('link', { name: 'Admin' })).toHaveAttribute('aria-current', 'page');
    await user.click(screen.getByRole('link', { name: 'Prices' }));
    expect(await screen.findByRole('table', { name: 'Drive prices' })).toBeVisible();
    expect(window.location.pathname).toBe('/');
    window.history.pushState(null, '', '/admin');
    window.dispatchEvent(new PopStateEvent('popstate'));
    expect(await screen.findByRole('heading', { name: 'Admin' })).toBeVisible();
  });

  it('adds an offer from the admin page too', async () => {
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('heading', { name: 'Admin' });
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    expect(screen.getByRole('dialog', { name: 'Add offer' })).toBeVisible();
  });

  it('keeps its links under the prefix the app is served from', async () => {
    window.history.replaceState(null, '', '/absproxy/5173/admin');
    renderApp({}, '/absproxy/5173/');
    expect(await screen.findByRole('heading', { name: 'Admin' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Admin' })).toHaveAttribute('href', '/absproxy/5173/admin');
    expect(screen.getByRole('link', { name: 'Prices' })).toHaveAttribute('href', '/absproxy/5173/');
    expect(screen.getByRole('link', { name: 'Stores' })).toHaveAttribute('href', '/absproxy/5173/admin/stores');
  });

  it('is split into To do, Stores and Drives, each with its own address', async () => {
    const user = userEvent.setup();
    renderApp({ list: async () => catalogue() });
    await screen.findByRole('heading', { name: 'Admin' });
    const tabs = within(screen.getByRole('navigation', { name: 'Admin sections' }));
    expect(tabs.getAllByRole('link').map(link => link.textContent)).toEqual(['To do (1)', 'Stores', 'Drives']);
    expect(tabs.getByRole('link', { name: 'To do (1)' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('region', { name: /Recheck by hand/ })).toBeVisible();
    expect(screen.queryByRole('region', { name: 'Stores' })).not.toBeInTheDocument();
    await user.click(tabs.getByRole('link', { name: 'Stores' }));
    expect(window.location.pathname).toBe('/admin/stores');
    expect(screen.getByRole('region', { name: 'Stores' })).toBeVisible();
    expect(screen.queryByRole('region', { name: /Recheck by hand/ })).not.toBeInTheDocument();
    await user.click(tabs.getByRole('link', { name: 'Drives' }));
    expect(window.location.pathname).toBe('/admin/drives');
    expect(screen.getByRole('table', { name: 'Drives' })).toBeVisible();
    expect(screen.getByRole('link', { name: /^Admin/ })).toHaveAttribute('aria-current', 'page');
    window.history.pushState(null, '', '/admin');
    window.dispatchEvent(new PopStateEvent('popstate'));
    expect(await screen.findByRole('region', { name: /Recheck by hand/ })).toBeVisible();
  });

  it('counts what is waiting, in the header and on the To do tab, and what is wrong with drives on theirs', async () => {
    const user = userEvent.setup();
    renderApp({ list: async () => catalogue(), listUnmatched: async () => [makeUnmatched('a'), makeUnmatched('b')] });
    expect(await screen.findByRole('link', { name: 'Admin 3 to do' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'To do (3)' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Recheck by hand (1)' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Needs matching (2)' })).toBeVisible();
    await user.click(screen.getByRole('link', { name: 'Drives' }));
    const drives = within(screen.getByRole('region', { name: 'Drives' }));
    expect(drives.getByRole('button', { name: 'Unknown specifications (2)' })).toBeVisible();
    expect(drives.getByRole('button', { name: 'Not checked in 7 days (1)' })).toBeVisible();
    // One store selling a drive is nothing to act on.
    expect(drives.queryByRole('button', { name: /Sold by one store/ })).not.toBeInTheDocument();
  });

  it('narrows the drive list to what a count counts, and choosing it again clears the filter', async () => {
    at('drives');
    const user = userEvent.setup();
    renderApp({ list: async () => catalogue() });
    await screen.findByRole('table', { name: 'Drives' });
    const attention = within(screen.getByRole('region', { name: 'Drives' }));
    await user.click(attention.getByRole('button', { name: /Not checked in 7 days/ }));
    expect(attention.getByRole('button', { name: /Not checked in 7 days/ })).toHaveAttribute('aria-pressed', 'true');
    expect(adminNames()).toEqual(['Ultrastar HC550']);
    await user.click(attention.getByRole('button', { name: /Unknown specifications/ }));
    expect(adminNames().sort()).toEqual(['Ultrastar HC550', 'WD Red Plus']);
    await user.click(attention.getByRole('button', { name: /Unknown specifications/ }));
    expect(adminNames()).toHaveLength(3);
  });

  it('finds drives by MPN', async () => {
    at('drives');
    const user = userEvent.setup();
    renderApp({ list: async () => catalogue() });
    await screen.findByRole('table', { name: 'Drives' });
    await user.type(screen.getByLabelText('Search drives'), 'wuh7218');
    expect(adminNames()).toEqual(['Ultrastar HC550']);
  });

  it("shows each store's last collector run and how fresh its prices are", async () => {
    at('stores');
    const runs = [run('goharddrive', { completed: false, seen: 12, recorded: 12, queued: 0, rechecked: 0 }), run('serverpartdeals')];
    renderApp({ list: async () => catalogue(), latestRuns: async () => runs });
    const table = within(await screen.findByRole('table', { name: 'Stores' }));
    expect(table.getAllByRole('columnheader').map(header => header.textContent))
      .toEqual(['Store', 'Collected', 'Schedule', 'Last run', 'Prices', 'Permission', 'Collect', 'Actions']);
    const cells = (store: string) => within(table.getByRole('row', { name: new RegExp(`^${store}`) })).getAllByRole('cell').map(cell => cell.textContent);
    const finished = new Date('2026-09-22T08:00:00Z').toLocaleString();
    await waitFor(() => expect(cells('GoHardDrive')[3]).toBe(`✕ Failed${finished}12 seen · 12 recorded · 0 queued · 0 failed · 0 rechecked`));
    expect(cells('ServerPartDeals')[3]).toBe(`✓ Completed${finished}70 seen · 68 recorded · 2 queued · 0 failed · 3 rechecked`);
    expect(cells('ServerPartDeals')[4]).toBe('2 offers' + 'median age 5 days');
    expect(cells('GoHardDrive')[4]).toBe('1 offer' + 'median age under an hour');
    expect(cells('Western Digital').slice(3, 5)).toEqual(['No run yet', '—']);
    // Other is entered by hand: nothing runs, but its prices still age.
    expect(cells('Other').slice(3, 5)).toEqual(['—', '1 offer' + 'median age under an hour']);
  });

  it('shows the run in progress, what waits behind it, and how each store stands', async () => {
    const user = userEvent.setup();
    renderApp({ list: async () => catalogue(), collectorStatus: async () => collecting() });
    const collectors = within(await screen.findByRole('region', { name: 'Collectors' }));
    expect(await collectors.findByText(/Running now/)).toHaveTextContent('Running now: GoHardDrive for 2 hours, 412 offers read so far.');
    expect(collectors.getByText(/^Waiting/)).toHaveTextContent('Waiting: ServerPartDeals, then Western Digital.');
    expect(collectors.queryByRole('alert')).not.toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: 'Stores' }));
    const table = within(screen.getByRole('table', { name: 'Stores' }));
    const cells = (store: string) => within(table.getByRole('row', { name: new RegExp(`^${store}`) })).getAllByRole('cell').map(cell => cell.textContent);
    expect(cells('GoHardDrive')[2]).toBe('0 */8 * * *' + 'Running now');
    expect(cells('GoHardDrive')[3]).toBe(`● Running` + `since ${new Date(ago(125)).toLocaleString()}` + '412 seen · 398 recorded · 9 queued · 5 ignored · 0 failed');
    expect(cells('ServerPartDeals')[2]).toBe('0 */8 * * *' + 'Next to run');
    expect(cells('Western Digital')[2]).toBe('0 */8 * * *' + 'Waiting, 2nd in line');
    // A store that is running is stopped, not started.
    expect(table.getByRole('button', { name: 'Stop GoHardDrive' })).toBeVisible();
    expect(table.queryByRole('button', { name: 'Run GoHardDrive now' })).not.toBeInTheDocument();
    expect(table.getByRole('button', { name: 'Run Western Digital now' })).toBeVisible();
  });

  it('stops a run in progress once that is confirmed', async () => {
    at('stores');
    const user = userEvent.setup();
    const stopSource = vi.fn<ListingsApi['stopSource']>(async id => makeSource(id, 'GoHardDrive'));
    renderApp({ list: async () => catalogue(), collectorStatus: async () => collecting(), stopSource });
    const row = within(await within(await screen.findByRole('table', { name: 'Stores' })).findByRole('row', { name: /^GoHardDrive/ }));
    await user.click(await row.findByRole('button', { name: 'Stop GoHardDrive' }));
    expect(row.getByText('Stop this run? What it has recorded is kept.')).toBeVisible();
    await user.click(row.getByRole('button', { name: 'Keep running' }));
    expect(stopSource).not.toHaveBeenCalled();
    await user.click(row.getByRole('button', { name: 'Stop GoHardDrive' }));
    await user.click(row.getByRole('button', { name: 'Yes, stop' }));
    expect(stopSource).toHaveBeenCalledWith('goharddrive');
    expect(await screen.findByRole('status')).toHaveTextContent('GoHardDrive was asked to stop: it ends once the offer it is reading is done.');
    // Until the collector has stopped, the run cannot be asked again.
    expect(row.getByRole('button', { name: 'Stopping GoHardDrive' })).toBeDisabled();
  });

  it('says when the collector has gone quiet, or has never been heard from', async () => {
    renderApp({ list: async () => catalogue(), collectorStatus: async () => collecting({ seen_at: ago(20) }) });
    const collectors = within(await screen.findByRole('region', { name: 'Collectors' }));
    expect(await collectors.findByRole('alert')).toHaveTextContent('The collector was last heard from 20 minutes ago. It may be down or restarting; a run shown as in progress may have ended with it.');
    cleanup();
    renderApp({ list: async () => catalogue(), collectorStatus: async () => ({ seen_at: null, running: [], waiting: [] }) });
    expect(await screen.findByText('No collector has been heard from yet.')).toBeVisible();
    cleanup();
    // Heard from, with nothing to do.
    renderApp({ list: async () => catalogue() });
    expect(await screen.findByText('Nothing is running or waiting to run.')).toBeVisible();
  });

  it('says a run that was stopped was stopped, not that it failed', async () => {
    at('stores');
    renderApp({ list: async () => catalogue(), latestRuns: async () => [run('goharddrive', { completed: false, stopped: true })] });
    const row = await within(await screen.findByRole('table', { name: 'Stores' })).findByRole('row', { name: /^GoHardDrive/ });
    await waitFor(() => expect(within(row).getAllByRole('cell')[3]).toHaveTextContent(/^■ Stopped/));
    expect(within(row).queryByText(/Failed/)).not.toBeInTheDocument();
  });

  it('lists the collectors whose last run failed among the things to do', async () => {
    const runs = [run('goharddrive', { completed: false }), run('serverpartdeals')];
    renderApp({ list: async () => catalogue(), latestRuns: async () => runs });
    const collectors = within(await screen.findByRole('region', { name: 'Collectors' }));
    expect(await collectors.findByText('1 of 2 collectors finished their last run.')).toBeVisible();
    expect(collectors.getAllByRole('listitem').map(item => item.textContent))
      .toEqual([`GoHardDrive failed · ${new Date('2026-09-22T08:00:00Z').toLocaleString()}`]);
    cleanup();
    renderApp({ list: async () => catalogue(), latestRuns: async () => [run('serverpartdeals')] });
    expect(await screen.findByText('All 1 collectors finished their last run.')).toBeVisible();
  });

  it('says there is nothing to do and no drives yet when nothing is recorded', async () => {
    const user = userEvent.setup();
    renderApp({ list: async () => [] });
    await screen.findByRole('heading', { name: 'Admin' });
    expect(screen.getByText('Everything entered by hand has been checked recently.')).toBeVisible();
    expect(screen.getByText('Nothing to match.')).toBeVisible();
    await user.click(screen.getByRole('link', { name: 'Drives' }));
    expect(within(screen.getByRole('region', { name: 'Drives' })).getByText('No drives yet.')).toBeVisible();
    expect(screen.queryByRole('table', { name: 'Drives' })).not.toBeInTheDocument();
  });

  it('says the collector runs could not be loaded rather than that there are none', async () => {
    renderApp({ list: async () => catalogue(), latestRuns: async () => { throw new Error('Unable to load runs (503).'); } });
    const collectors = within(await screen.findByRole('region', { name: 'Collectors' }));
    expect(await collectors.findByRole('alert')).toHaveTextContent('Collector runs could not be loaded: Unable to load runs (503).');
    expect(collectors.queryByText('No collector runs reported yet.')).not.toBeInTheDocument();
  });

  it('says so when no collector has reported a run', async () => {
    renderApp({ list: async () => catalogue() });
    expect(await screen.findByText('No collector runs reported yet.')).toBeVisible();
  });

  it('refreshes the price change after deleting a wrong price', async () => {
    at('drives');
    const user = userEvent.setup();
    let listing = makeListing('History drive', { observations: historyPrices, latest: historyPrices[1] });
    const deletePrice = vi.fn<ListingsApi['deletePrice']>(async () => {
      listing = { ...listing, latest: historyPrices[0], observations: [historyPrices[0]] };
      return listing;
    });
    renderApp({ list: async () => [listing], deletePrice });
    await user.click(await screen.findByRole('button', { name: 'History drive' }));
    const offer = () => within(within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('row')[1]);
    expect(offer().getByText('▼ $15.00 (6.5%)')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Price history (2)' }));
    const history = within(screen.getByRole('table', { name: 'Price history' }));
    await user.click(history.getAllByRole('button', { name: 'Delete price' })[1]);
    const confirm = within(screen.getByRole('dialog', { name: 'Delete price' }));
    expect(confirm.getByText(/\$195\.00 from Example seller/)).toBeVisible();
    await user.click(confirm.getByRole('button', { name: 'Delete' }));
    expect(deletePrice).toHaveBeenCalledWith('History drive', 'current');
    expect(await offer().findByText('$230.00')).toBeVisible();
    expect(offer().queryByText(/[▼▲]/)).not.toBeInTheDocument();
    expect(history.getAllByRole('row')).toHaveLength(2);
  });

  it('edits specifications once for every listing of the drive', async () => {
    at('drives');
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    let listings = [
      makeListing('Verified drive', { drive, mpn: drive.mpn, seller: 'ServerPartDeals' }),
      makeListing('Other seller', { drive, mpn: drive.mpn, seller: 'GoHardDrive' }, { total_cents: 99999, price_per_tb: '99.99' }),
    ];
    const replaceSpecifications = vi.fn<ListingsApi['replaceSpecifications']>(async (_id, input) => {
      const updated = { ...drive, ...input };
      listings = listings.map(listing => ({ ...listing, drive: updated, capacity_gb: input.capacity_gb }));
      return updated;
    });
    renderApp({ list: async () => listings, replaceSpecifications });
    await user.click(await screen.findByRole('button', { name: 'Verified drive' }));
    await user.click(screen.getByRole('button', { name: 'Edit specifications' }));
    const form = within(screen.getByRole('dialog', { name: 'Edit specifications' }));
    expect(form.getByLabelText('Capacity', { exact: true })).toHaveValue('18000');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Interface', { exact: true }), 'sata');
    await user.selectOptions(form.getByLabelText('Recording type', { exact: true }), 'cmr');
    await user.click(form.getByLabelText('NAS', { exact: true }));
    await user.click(form.getByLabelText('Enterprise', { exact: true }));
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(replaceSpecifications).toHaveBeenCalledWith(drive.id, {
      capacity_gb: 20000,
      specifications: { ...emptySpecifications(), interface: 'sata', recording_type: 'cmr', intended_use: ['nas', 'enterprise'] },
      brand: '',
    });
    expect(await screen.findByText('Specifications saved for every offer of MPN ST18000NM003D.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Specifications' }));
    const details = within(screen.getByRole('region', { name: 'Drive specifications' }));
    expect(details.getByText('SATA')).toBeVisible();
    expect(details.getByText('NAS, Enterprise')).toBeVisible();
  }, 15000);

  it('deletes a price from the right listing in the combined history', async () => {
    at('drives');
    const user = userEvent.setup();
    const drive = makeDrive('ST18000NM003D');
    const fromServerPartDeals = makeListing('from-serverpartdeals', { drive, title: 'Seagate Exos X20', seller: 'ServerPartDeals' },
      { total_cents: 49900, observed_at: '2026-09-20T12:00:00Z', entered_at: '2026-09-20T12:00:00Z' });
    const fromOther = makeListing('from-other', { drive, title: 'Seagate Exos X20', seller: 'drivedeals' },
      { total_cents: 48700, observed_at: '2026-09-21T12:00:00Z', entered_at: '2026-09-21T12:00:00Z' });
    const deletePrice = vi.fn<ListingsApi['deletePrice']>(async () => fromOther);
    renderApp({ list: async () => [fromServerPartDeals, fromOther], deletePrice });
    await user.click(await screen.findByRole('button', { name: 'Seagate Exos X20' }));
    await user.click(screen.getByRole('button', { name: 'Price history (2)' }));
    const rows = within(screen.getByRole('table', { name: 'Price history' })).getAllByRole('row').slice(1);
    await user.click(within(rows[1]).getByRole('button', { name: 'Delete price' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Delete price' })).getByRole('button', { name: 'Delete' }));
    expect(deletePrice).toHaveBeenCalledWith('from-other', 'from-other-observation');
  });

  it("edits an offer's title and URL in place from its menu, leaving capacity to the drive", async () => {
    at('drives');
    const user = userEvent.setup();
    let listing = makeListing('Drive', { mpn: 'ST18000NM000J', url: 'https://example.com/old' });
    const editOffer = vi.fn<ListingsApi['editOffer']>(async (_id, input) => {
      listing = { ...listing, ...input };
      return listing;
    });
    renderApp({ list: async () => [listing], editOffer });
    await user.click(await screen.findByRole('button', { name: 'Drive' }));
    await user.click(screen.getByRole('button', { name: 'More actions for Example seller' }));
    await user.click(screen.getByRole('menuitem', { name: 'Edit offer' }));
    const form = within(screen.getByRole('dialog', { name: 'Edit offer' }));
    expect(form.getByText('ST18000NM000J · Example seller · New')).toBeVisible();
    const title = form.getByRole('textbox', { name: 'Offer title' });
    await user.clear(title);
    await user.type(title, 'Exos X18');
    expect(form.queryByLabelText('Capacity', { exact: true })).not.toBeInTheDocument();
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(editOffer).toHaveBeenCalledWith('Drive', { title: 'Exos X18', url: 'https://example.com/old' });
    expect(await screen.findByRole('dialog', { name: 'Exos X18' })).toBeVisible();
  });

  it('removes an offer when its only price is deleted, and cancelling a delete keeps the price', async () => {
    at('drives');
    const user = userEvent.setup();
    let listings = [makeListing('Drive'), makeListing('Other drive')];
    const deletePrice = vi.fn<ListingsApi['deletePrice']>(async () => {
      listings = listings.filter(listing => listing.id !== 'Drive');
      return null;
    });
    renderApp({ list: async () => listings, deletePrice });
    await user.click(await screen.findByRole('button', { name: 'Drive' }));
    await user.click(screen.getByRole('button', { name: 'Price history (1)' }));
    await user.click(screen.getByRole('button', { name: 'Delete price' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Delete price' })).getByRole('button', { name: 'Cancel' }));
    expect(deletePrice).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Delete price' }));
    const confirm = within(screen.getByRole('dialog', { name: 'Delete price' }));
    expect(confirm.getByText(/only price, so the offer is removed too/)).toBeVisible();
    await user.click(confirm.getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Drive' })).not.toBeInTheDocument());
    expect(adminNames()).toEqual(['Other drive']);
  });

  it('deletes an offer from its menu after confirming', async () => {
    at('drives');
    const user = userEvent.setup();
    let listings = [makeListing('Duplicate'), makeListing('Keep')];
    const deleteOffer = vi.fn<ListingsApi['deleteOffer']>(async id => {
      listings = listings.filter(listing => listing.id !== id);
    });
    renderApp({ list: async () => listings, deleteOffer });
    await user.click(await screen.findByRole('button', { name: 'Duplicate' }));
    await user.click(screen.getByRole('button', { name: 'More actions for Example seller' }));
    await user.click(screen.getByRole('menuitem', { name: 'Delete offer' }));
    const confirm = within(screen.getByRole('dialog', { name: 'Delete offer' }));
    expect(confirm.getByText(/Duplicate · Example seller · New and its 1 price/)).toBeVisible();
    await user.click(confirm.getByRole('button', { name: 'Delete' }));
    expect(deleteOffer).toHaveBeenCalledWith('Duplicate');
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Duplicate' })).not.toBeInTheDocument());
    expect(adminNames()).toEqual(['Keep']);
    expect(screen.getByText('Offer deleted.')).toBeVisible();
  });

  it('adds another MPN for a drive so variant listings join it', async () => {
    at('drives');
    const user = userEvent.setup();
    let drive = makeDrive('ST18000NM000J');
    const variantDrive = makeDrive('ST18000NM000J-2E3101');
    let listings = [
      makeListing('Exos X18', { drive, mpn: drive.mpn, seller: 'Shop A' }),
      makeListing('Exos X18 variant', { drive: variantDrive, mpn: variantDrive.mpn, seller: 'Shop B' }),
    ];
    const addAlias = vi.fn<ListingsApi['addAlias']>(async (_id, mpn) => {
      drive = { ...drive, aliases: [mpn.toUpperCase()] };
      listings = listings.map(listing => ({ ...listing, drive, mpn: drive.mpn }));
      return drive;
    });
    renderApp({ list: async () => listings, addAlias });
    await user.click(await screen.findByRole('button', { name: 'Exos X18' }));
    await user.click(screen.getByRole('button', { name: 'Edit specifications' }));
    const form = within(screen.getByRole('dialog', { name: 'Edit specifications' }));
    await user.type(form.getByRole('textbox', { name: 'Other MPN' }), 'st18000nm000j-2e3101');
    await user.click(form.getByRole('button', { name: 'Add MPN' }));
    expect(addAlias).toHaveBeenCalledWith(drive.id, 'st18000nm000j-2e3101');
    expect(await form.findByText('ST18000NM000J-2E3101')).toBeVisible();
    await waitFor(() => expect(screen.getByText('MPN ST18000NM000J · 2 stores · 2 offers')).toBeVisible());
  });

  it('leaves the page message alone when another MPN is added', async () => {
    at('drives');
    const user = userEvent.setup();
    let drive = makeDrive('ST18000NM000J');
    let listing = makeListing('Exos X18', { drive, mpn: drive.mpn });
    const editOffer = vi.fn<ListingsApi['editOffer']>(async (_id, input) => { listing = { ...listing, ...input }; return listing; });
    const addAlias = vi.fn<ListingsApi['addAlias']>(async (_id, mpn) => {
      drive = { ...drive, aliases: [mpn.toUpperCase()] };
      listing = { ...listing, drive };
      return drive;
    });
    renderApp({ list: async () => [listing], editOffer, addAlias });
    await user.click(await screen.findByRole('button', { name: 'Exos X18' }));
    await user.click(screen.getByRole('button', { name: 'More actions for Example seller' }));
    await user.click(screen.getByRole('menuitem', { name: 'Edit offer' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Edit offer' })).getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('Offer updated.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Edit specifications' }));
    const form = within(screen.getByRole('dialog', { name: 'Edit specifications' }));
    await user.type(form.getByRole('textbox', { name: 'Other MPN' }), 'ST18000NM000J-2E3101');
    await user.click(form.getByRole('button', { name: 'Add MPN' }));
    expect(await form.findByText('ST18000NM000J-2E3101')).toBeVisible();
    expect(screen.getByText('Offer updated.')).toBeInTheDocument();
  });

  it('lists hand-entered offers overdue for a check, oldest first, each with a link to the listing', async () => {
    const offer = (title: string, days: number, fields = {}, price = {}) => makeListing(title, {
      mpn: 'WD120EFBX', store: 'other', seller: 'Micro Center', last_checked_at: daysAgo(days), url: `https://store.test/${days}`, ...fields,
    }, { observed_at: daysAgo(days), entered_at: daysAgo(days), ...price });
    const listings = [
      offer('Checked 20 days ago', 20),
      offer('Checked 30 days ago', 30),
      offer('Checked today', 0),
      offer('Collected', 40, { store: 'serverpartdeals', seller: '' }, { acquisition_method: 'serverpartdeals' }),
    ];
    renderApp({ list: async () => listings });
    const recheck = within(await screen.findByRole('region', { name: /Recheck by hand/ }));
    const rows = recheck.getAllByRole('row').slice(1);
    expect(rows.map(row => within(row).getAllByRole('cell')[0].textContent)).toEqual(['Checked 30 days ago', 'Checked 20 days ago']);
    expect(within(rows[1]).getByRole('link', { name: /Open store page/ })).toHaveAttribute('href', 'https://store.test/20');
  });

  it('records that a rechecked offer is still the same price, or a new price, or out of stock, in one step each', async () => {
    const user = userEvent.setup();
    const listing = makeListing('WD Red Plus 12TB', {
      mpn: 'WD120EFBX', store: 'other', seller: 'Micro Center', url: 'https://store.test/red', last_checked_at: daysAgo(20),
    }, { observed_at: daysAgo(20), entered_at: daysAgo(20), item_price_cents: 20000, shipping_cents: 500, total_cents: 20500 });
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    renderApp({ list: async () => [listing], recordPrice });
    const row = () => within(within(screen.getByRole('region', { name: /Recheck by hand/ })).getAllByRole('row')[1]);
    const identity = {
      mpn: 'WD120EFBX', store: 'other', seller: 'Micro Center', condition: 'new', title: 'WD Red Plus 12TB',
      url: 'https://store.test/red', capacity_gb: null, observed_at: null, notes: '',
    };
    await screen.findByRole('region', { name: /Recheck by hand/ });
    await user.click(row().getByRole('button', { name: 'No change' }));
    expect(recordPrice).toHaveBeenLastCalledWith({ ...identity, item_price_cents: 20000, shipping_cents: 500, in_stock: true }, 'save-key');
    await user.type(row().getByRole('textbox', { name: 'New price for WD Red Plus 12TB' }), '189.99{Enter}');
    expect(recordPrice).toHaveBeenLastCalledWith({ ...identity, item_price_cents: 18999, shipping_cents: 500, in_stock: true }, 'save-key');
    await user.click(row().getByRole('button', { name: 'Out of stock' }));
    expect(recordPrice).toHaveBeenLastCalledWith({ ...identity, item_price_cents: null, shipping_cents: 500, in_stock: false }, 'save-key');
  });

  it('says what is wrong with a new price it cannot read, and records nothing', async () => {
    const user = userEvent.setup();
    const listing = makeListing('WD Red Plus 12TB', { mpn: 'WD120EFBX', last_checked_at: daysAgo(20) }, { observed_at: daysAgo(20) });
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    renderApp({ list: async () => [listing], recordPrice });
    const recheck = within(await screen.findByRole('region', { name: /Recheck by hand/ }));
    await user.type(recheck.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' }), '18.999{Enter}');
    expect(recheck.getByRole('alert')).toHaveTextContent('Enter a non-negative amount with up to two decimal places.');
    expect(recordPrice).not.toHaveBeenCalled();
  });

  it('adds a store entered by hand, which the listing filters and Add price then offer', async () => {
    at('stores');
    const user = userEvent.setup();
    let known = [makeSource('serverpartdeals', 'ServerPartDeals'), makeSource('other', 'Other', { kind: 'manual' })];
    const addSource = vi.fn<ListingsApi['addSource']>(async input => {
      const added = { ...input, id: 'orbit', key: 'serverorbit', next_run_at: null };
      known = [...known, added];
      return added;
    });
    renderApp({ listSources: async () => known, addSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'ServerOrbit');
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'manual');
    expect(form.getByLabelText('Store URL', { exact: true })).not.toBeRequired();
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(addSource).toHaveBeenLastCalledWith({
      name: 'ServerOrbit', kind: 'manual', base_url: '', settings: {},
      schedule: '0 */8 * * *', enabled: true, transport: 'direct', basis: 'unconfirmed', notes: '',
    });
    const row = within(await within(section.getByRole('table', { name: 'Stores' })).findByRole('row', { name: /ServerOrbit/ }));
    expect(row.getAllByRole('cell').map(cell => cell.textContent).slice(0, 2)).toEqual(['ServerOrbit', 'Entered by hand']);
    // Nothing to collect: no switch and no Run now.
    expect(row.queryByRole('switch')).not.toBeInTheDocument();
    expect(row.queryByRole('button', { name: 'Run ServerOrbit now' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: 'Prices' }));
    await screen.findByRole('heading', { name: 'Prices' });
    await user.click(screen.getByRole('button', { name: 'More filters' }));
    await user.click(screen.getByRole('textbox', { name: 'Store' }));
    expect(screen.getByRole('option', { name: 'ServerOrbit' })).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Add offer' }));
    const price = within(screen.getByRole('dialog', { name: 'Add offer' }));
    expect(within(price.getByLabelText('Store', { exact: true })).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Choose store', 'ServerPartDeals', 'Other', 'ServerOrbit']);
  }, 20000);

  it('adds a source that collects on a cron schedule, and switches it off', async () => {
    at('stores');
    const user = userEvent.setup();
    let sources: Source[] = [];
    const saved = (input: SourceInput, id: string): Source => ({ ...input, id, key: 'serverpartdeals', next_run_at: '2026-09-23T03:00:00Z' });
    const addSource = vi.fn<ListingsApi['addSource']>(async input => {
      if (input.schedule === 'nightly') throw new ApiValidationError({ schedule: 'Enter a cron schedule, e.g. 0 3 * * *.' });
      sources = [...sources, saved(input, 'spd')];
      return sources[0];
    });
    const updateSource = vi.fn<ListingsApi['updateSource']>(async (id, input) => {
      sources = sources.map(source => source.id === id ? saved(input, id) : source);
      return sources[0];
    });
    renderApp({ listSources: async () => sources, addSource, updateSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    expect(await section.findByText('No stores yet.')).toBeVisible();
    await user.click(section.getByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'ServerPartDeals');
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'shopify');
    await user.type(form.getByLabelText('Collections', { exact: true }), 'hard-drives, solid-state-drives');
    // The collector works out whether a store's SKUs are part numbers.
    expect(form.queryByLabelText('The SKU is the MPN', { exact: true })).not.toBeInTheDocument();
    // Sold-out prices are never recorded, so there is no placeholder price to name.
    expect(form.queryByLabelText('Placeholder price (USD)', { exact: true })).not.toBeInTheDocument();
    await user.type(form.getByLabelText('Store URL', { exact: true }), 'https://www.serverpartdeals.com');
    // Optional settings wait under Advanced.
    expect(form.queryByLabelText('Every order ships free', { exact: true })).not.toBeInTheDocument();
    await user.click(form.getByRole('button', { name: 'Advanced' }));
    await user.click(form.getByLabelText('Every order ships free', { exact: true }));
    await user.clear(form.getByLabelText('Schedule (cron)', { exact: true }));
    await user.type(form.getByLabelText('Schedule (cron)', { exact: true }), 'nightly');
    await user.selectOptions(form.getByLabelText('Permission', { exact: true }), 'unconfirmed');
    expect(form.getByLabelText('Fetch pages', { exact: true })).toHaveValue('direct');
    await user.selectOptions(form.getByLabelText('Fetch pages', { exact: true }), 'browser');
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(await form.findByText('Enter a cron schedule, e.g. 0 3 * * *.')).toBeVisible();
    await user.clear(form.getByLabelText('Schedule (cron)', { exact: true }));
    await user.type(form.getByLabelText('Schedule (cron)', { exact: true }), '0 3 * * *');
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(addSource).toHaveBeenLastCalledWith({
      name: 'ServerPartDeals', kind: 'shopify', base_url: 'https://www.serverpartdeals.com',
      settings: { collections: ['hard-drives', 'solid-state-drives'], free_shipping: true },
      schedule: '0 3 * * *', enabled: true, transport: 'browser', basis: 'unconfirmed', notes: '',
    });
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Add store' })).not.toBeInTheDocument());
    const row = within(within(section.getByRole('table', { name: 'Stores' })).getAllByRole('row')[1]);
    const cells = row.getAllByRole('cell').map(cell => cell.textContent);
    expect(cells.slice(0, 3)).toEqual(['ServerPartDeals', 'Shopify', `0 3 * * *Next ${new Date('2026-09-23T03:00:00Z').toLocaleString()}`]);
    expect(cells[5]).toBe('Unconfirmed');
    await user.click(row.getByRole('switch', { name: 'Collect from ServerPartDeals' }));
    expect(updateSource).toHaveBeenCalledWith('spd', expect.objectContaining({ enabled: false }));
  }, 20000);

  it('adds a source from just its name, type and store URL', async () => {
    at('stores');
    const user = userEvent.setup();
    const addSource = vi.fn<ListingsApi['addSource']>(async input => ({
      ...input, id: 'orbit', key: 'serverorbit', next_run_at: null,
    }));
    renderApp({ listSources: async () => [], addSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'Server Orbit');
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'shopify');
    await user.type(form.getByLabelText('Collections', { exact: true }), 'hard-drives');
    await user.type(form.getByLabelText('Store URL', { exact: true }), 'https://www.serverorbit.com');
    expect(form.queryByLabelText('Schedule (cron)', { exact: true })).not.toBeInTheDocument();
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(addSource).toHaveBeenLastCalledWith({
      name: 'Server Orbit', kind: 'shopify', base_url: 'https://www.serverorbit.com',
      settings: { collections: ['hard-drives'], free_shipping: false },
      schedule: '0 */8 * * *', enabled: true, transport: 'direct', basis: 'unconfirmed', notes: '',
    });
  }, 20000);

  it('tests a source from the form before saving it: one offer as read, and what would become of it', async () => {
    at('stores');
    const user = userEvent.setup();
    const offer: SourcePreview['offer'] = {
      url: 'https://www.serverorbit.com/products/exos-x18', title: 'Seagate Exos X18 ST18000NM000J 18TB', mpn: 'ST18000NM000J',
      brand: 'Seagate', condition: 'manufacturer_recertified', capacity_gb: 18000, item_price_cents: 36999, shipping_cents: 0,
      in_stock: true, aliases: [],
    };
    const answers: (SourcePreview | Error)[] = [
      new ApiValidationError({ 'settings.collections': 'List should have at least 1 item after validation, not 0' }),
      new Error('No collector is configured, so sources cannot be tested.'),
      { status: 'failed', reason: 'robots.txt disallows https://www.serverorbit.com/collections/x', offer: null, verdict: null, notes: [] },
      { status: 'nothing', reason: null, offer: null, verdict: null, notes: [] },
      { status: 'found', reason: null, offer: { ...offer, mpn: null }, verdict: { outcome: 'review', reason: 'missing_mpn' }, notes: [] },
      { status: 'found', reason: null, offer, verdict: { outcome: 'recorded', reason: null }, notes: [] },
    ];
    const previewSource = vi.fn<ListingsApi['previewSource']>(async () => {
      const answer = answers.shift()!;
      if (answer instanceof Error) throw answer;
      return answer;
    });
    const addSource = vi.fn<ListingsApi['addSource']>();
    renderApp({ listSources: async () => [], previewSource, addSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'Server Orbit');
    // A store entered by hand has nothing to read.
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'manual');
    expect(form.queryByRole('button', { name: 'Test' })).not.toBeInTheDocument();
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'shopify');
    await user.type(form.getByLabelText('Store URL', { exact: true }), 'https://www.serverorbit.com');
    const test = () => user.click(form.getByRole('button', { name: 'Test' }));

    await test();
    expect(await form.findByText('List should have at least 1 item after validation, not 0')).toBeVisible();
    await user.type(form.getByLabelText('Collections', { exact: true }), 'hard-drives');
    await test();
    expect(await form.findByText('No collector is configured, so sources cannot be tested.')).toBeVisible();
    // Each test replaces the last result.
    await test();
    expect(await form.findByText('The store could not be read: robots.txt disallows https://www.serverorbit.com/collections/x')).toBeVisible();
    await test();
    expect(await form.findByText('The store was read, but no drive was found.')).toBeVisible();
    await test();
    expect(await form.findByText('It would wait under Needs matching: no MPN was read.')).toBeVisible();
    await test();
    expect(await form.findByText('It would be recorded.')).toBeVisible();
    const result = within(form.getByRole('region', { name: 'Test result' }));
    expect(result.getByRole('link', { name: 'Seagate Exos X18 ST18000NM000J 18TB' })).toHaveAttribute('href', offer.url);
    expect(result.getAllByRole('definition').map(item => item.textContent)).toEqual([
      'ST18000NM000J', 'Seagate', 'Manufacturer recertified', '18 TB', '$369.99', 'Free', 'In stock',
    ]);

    expect(previewSource).toHaveBeenLastCalledWith({
      name: 'Server Orbit', kind: 'shopify', base_url: 'https://www.serverorbit.com',
      settings: { collections: ['hard-drives'], free_shipping: false },
      schedule: '0 */8 * * *', enabled: true, transport: 'direct', basis: 'unconfirmed', notes: '',
    });
    expect(addSource).not.toHaveBeenCalled();
  }, 30000);

  it('asks for whatever settings a kind of store is described as having', async () => {
    at('stores');
    const user = userEvent.setup();
    // A kind this app has never heard of: all it knows of it is its description.
    const magento: SourceKindDescription = {
      kind: 'magento', label: 'Magento', collected: true, page_test: true,
      groups: [{ name: 'api', label: 'Storefront API', help: 'Only for stores that publish one.' }],
      settings: [
        { name: 'store_view', label: 'Store view', type: 'text', required: true, description: 'The code of the view to read', placeholder: 'default', group: '', pattern: '', pattern_message: '', regex: false, capturing: false, needs: '' },
        { name: 'categories', label: 'Categories', type: 'list', required: false, description: '', placeholder: '', group: '', pattern: '', pattern_message: '', regex: false, capturing: false, needs: '' },
        { name: 'guest', label: 'Read as a guest', type: 'flag', required: false, description: '', placeholder: '', group: 'api', pattern: '', pattern_message: '', regex: false, capturing: false, needs: '' },
      ],
    };
    const addSource = vi.fn<ListingsApi['addSource']>(async input => ({ ...input, id: 'm', key: 'shop', next_run_at: null }));
    renderApp({ listSources: async () => [], listSourceKinds: async () => [magento], addSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'Shop');
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'Magento');
    await user.type(form.getByLabelText('Store URL', { exact: true }), 'https://shop.test');
    // What must be given is asked for at once; the rest waits under Advanced, grouped as described.
    await user.type(form.getByLabelText('Store view', { exact: true }), 'default');
    expect(form.getByText('The code of the view to read')).toBeVisible();
    expect(form.queryByLabelText('Categories', { exact: true })).not.toBeInTheDocument();
    expect(form.getByLabelText('Page to test', { exact: true })).toBeVisible();
    await user.click(form.getByRole('button', { name: 'Advanced' }));
    await user.type(form.getByLabelText('Categories', { exact: true }), 'drives, ssds');
    await user.click(form.getByRole('button', { name: 'Storefront API' }));
    expect(form.getByText('Only for stores that publish one.')).toBeVisible();
    await user.click(form.getByLabelText('Read as a guest', { exact: true }));
    await user.click(form.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(addSource).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'magento', settings: { store_view: 'default', categories: ['drives', 'ssds'], guest: true },
    })));
  }, 30000);

  it('names each store\'s kind as the kind is described', async () => {
    at('stores');
    renderApp({
      listSources: async () => [makeSource('shop', 'Shop', { kind: 'magento' })],
      listSourceKinds: async () => [{ kind: 'magento', label: 'Magento', collected: true, page_test: false, groups: [], settings: [] }],
    });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    expect(await section.findByText('Magento')).toBeVisible();
  });

  it('inspects a link to a new store and fills the form with the settings found for it', async () => {
    at('stores');
    const user = userEvent.setup();
    const link = 'https://www.seagate.com/products/nas-drives/ironwolf-pro-hard-drive/';
    const settings = {
      sitemap_path: '/sitemap.xml', product_path_pattern: '^/products/', free_shipping_marker: '',
      data_pattern: "product_models = JSON\\.parse\\('(.*?)'\\);", data_items: '*.skus.*', data_model_field: 'modelNo',
      data_name_field: 'name', data_price_field: 'final_price', data_brand_field: 'brand', data_stock_field: 'stock_status', data_in_stock_value: 'IN_STOCK',
    };
    const answers: SourceInspection[] = [
      { status: 'failed', reason: "Client error '403 FORBIDDEN'", base_url: 'https://www.seagate.com', candidates: [], notes: [] },
      { status: 'nothing', reason: null, base_url: 'https://www.seagate.com', candidates: [], notes: ["No price was found in the page's markup or JSON-LD."] },
      {
        status: 'found', reason: null, base_url: 'https://www.seagate.com', notes: [],
        candidates: [{
          kind: 'sitemap', settings, offers: 8, verdict: { outcome: 'ignored', reason: 'sold_out' },
          summary: [{ label: 'Pages a run would fetch', value: '145' }, { label: 'Time for a run', value: 'about 49 minutes (146 requests, 20 seconds apart)' }],
          evidence: ['The page carries its products as data in one of its scripts.', "The page is in the store's sitemap, /sitemap.xml, which lists 5,441 pages."],
          offer: {
            url: link, title: 'IronWolf Pro 32TB', mpn: 'ST32000NT000', brand: 'Seagate', condition: 'new', capacity_gb: 32000,
            item_price_cents: 139999, shipping_cents: null, in_stock: false, aliases: [],
          },
        }],
      },
    ];
    const inspectLink = vi.fn<ListingsApi['inspectLink']>(async () => answers.shift()!);
    const addSource = vi.fn<ListingsApi['addSource']>(async input => ({ ...input, id: 'seagate', key: 'seagate', next_run_at: null }));
    renderApp({ listSources: async () => [], inspectLink, addSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Product link', { exact: true }), link);
    const inspect = () => user.click(form.getByRole('button', { name: 'Inspect' }));

    await inspect();
    expect(await form.findByText("The page could not be read: Client error '403 FORBIDDEN'")).toBeVisible();
    await inspect();
    expect(await form.findByText('The page was read, but no way of reading a drive from it was found.')).toBeVisible();
    expect(form.getByText("No price was found in the page's markup or JSON-LD.")).toBeVisible();
    await inspect();
    const found = within(await form.findByRole('region', { name: 'Inspection result' }));
    expect(found.getByText('8 offers read with these settings; the first:')).toBeVisible();
    expect(found.getByRole('link', { name: 'IronWolf Pro 32TB' })).toHaveAttribute('href', link);
    expect(found.getAllByRole('listitem').map(item => item.textContent)).toEqual([
      'The page carries its products as data in one of its scripts.',
      "The page is in the store's sitemap, /sitemap.xml, which lists 5,441 pages.",
    ]);
    // How much there is to the store, to judge whether it is worth adding.
    const store = within(found.getByRole('group', { name: 'About the store' }));
    expect(store.getAllByRole('term').map(term => term.textContent)).toEqual(['Pages a run would fetch', 'Time for a run']);
    expect(store.getAllByRole('definition').map(value => value.textContent)).toEqual(['145', 'about 49 minutes (146 requests, 20 seconds apart)']);
    expect(inspectLink).toHaveBeenLastCalledWith(link, 'direct');

    await user.click(form.getByRole('button', { name: 'Use these settings' }));
    expect(form.getByLabelText('Name', { exact: true })).toHaveValue('Seagate');
    expect(form.getByLabelText('Type', { exact: true })).toHaveValue('sitemap');
    expect(form.getByLabelText('Store URL', { exact: true })).toHaveValue('https://www.seagate.com');
    // The link becomes the page Test reads.
    expect(form.getByLabelText('Page to test', { exact: true })).toHaveValue(link);
    await user.click(form.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(addSource).toHaveBeenCalledWith(expect.objectContaining({
      name: 'Seagate', kind: 'sitemap', base_url: 'https://www.seagate.com',
      settings: Object.fromEntries(Object.entries(settings).filter(([, value]) => value)),
    })));
  }, 30000);

  it('says why a link could not be inspected, and keeps a name already typed when settings are taken', async () => {
    at('stores');
    const user = userEvent.setup();
    const link = 'https://www.disctech.com/Toshiba-MG07ACA14TEY-14TB';
    const found: SourceInspection = {
      status: 'found', reason: null, base_url: 'https://www.disctech.com', notes: [],
      candidates: [{
        kind: 'sitemap', settings: { sitemap_path: '/sitemap.xml' }, offers: 1, summary: [], evidence: [],
        verdict: { outcome: 'recorded', reason: null },
        offer: {
          url: link, title: 'Toshiba MG07ACA14TEY 14TB', mpn: 'MG07ACA14TEY', brand: 'Toshiba', condition: 'refurbished',
          capacity_gb: 14000, item_price_cents: 28999, shipping_cents: null, in_stock: true, aliases: [],
        },
      }],
    };
    const answers: (SourceInspection | Error)[] = [new Error('No collector is configured, so sources cannot be tested.'), found];
    const inspectLink = vi.fn<ListingsApi['inspectLink']>(async () => {
      const answer = answers.shift()!;
      if (answer instanceof Error) throw answer;
      return answer;
    });
    renderApp({ listSources: async () => [], inspectLink });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'Disc Tech (refurbished)');
    await user.type(form.getByLabelText('Product link', { exact: true }), link);
    await user.click(form.getByRole('button', { name: 'Inspect' }));
    expect(await form.findByText('No collector is configured, so sources cannot be tested.')).toBeVisible();
    await user.click(form.getByRole('button', { name: 'Inspect' }));
    await user.click(await form.findByRole('button', { name: 'Use these settings' }));
    // With nothing known about the store, nothing is said about it.
    expect(form.queryByRole('group', { name: 'About the store' })).not.toBeInTheDocument();
    expect(form.getByLabelText('Name', { exact: true })).toHaveValue('Disc Tech (refurbished)');
    expect(form.getByLabelText('Store URL', { exact: true })).toHaveValue('https://www.disctech.com');
  }, 30000);

  it('says so when the kinds of store cannot be loaded, and still lists the stores', async () => {
    at('stores');
    renderApp({
      listSources: async () => [makeSource('goharddrive', 'GoHardDrive', { kind: 'sitemap' }), makeSource('other', 'Other', { kind: 'manual' })],
      listSourceKinds: async () => { throw new Error('Unable to save or load listings (503).'); },
    });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    expect(await section.findByRole('alert')).toHaveTextContent('Unable to save or load listings (503).');
    // Without their descriptions a kind goes by its bare name, and a store entered by hand is still known for one.
    expect(section.getByText('sitemap')).toBeVisible();
    expect(section.getByRole('button', { name: 'Run GoHardDrive now' })).toBeVisible();
    expect(section.queryByRole('button', { name: 'Run Other now' })).not.toBeInTheDocument();
  });

  it('offers to inspect a link only for a store being added', async () => {
    at('stores');
    const user = userEvent.setup();
    renderApp({ listSources: async () => [makeSource('goharddrive', 'GoHardDrive', { kind: 'sitemap' })] });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: /^Edit/ }));
    const form = within(screen.getByRole('dialog', { name: 'Edit store' }));
    expect(form.queryByLabelText('Product link', { exact: true })).not.toBeInTheDocument();
  });

  it('tests a sitemap source on one of its pages, and shows what the collector read', async () => {
    at('stores');
    const user = userEvent.setup();
    const page = 'https://www.seagate.com/products/nas-drives/ironwolf-pro-hard-drive/';
    const answers: (SourcePreview | Error)[] = [
      new ApiValidationError({ page_url: "Enter the page's address, starting http:// or https://." }),
      {
        status: 'nothing', reason: null, offer: null, verdict: null,
        notes: [`${page}: 16 products in its data: 16 with no price`],
      },
    ];
    const previewSource = vi.fn<ListingsApi['previewSource']>(async () => {
      const answer = answers.shift()!;
      if (answer instanceof Error) throw answer;
      return answer;
    });
    renderApp({ listSources: async () => [], previewSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'Seagate');
    // Only a store read page by page has a page to test.
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'shopify');
    expect(form.queryByLabelText('Page to test', { exact: true })).not.toBeInTheDocument();
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'sitemap');
    await user.type(form.getByLabelText('Store URL', { exact: true }), 'https://www.seagate.com');
    const pageInput = form.getByLabelText('Page to test', { exact: true });
    await user.type(pageInput, 'ironwolf-pro');
    await user.click(form.getByRole('button', { name: 'Test' }));
    expect(await form.findByText("Enter the page's address, starting http:// or https://.")).toBeVisible();
    await user.clear(pageInput);
    await user.type(pageInput, page);
    await user.click(form.getByRole('button', { name: 'Test' }));

    expect(await form.findByText('The store was read, but no drive was found.')).toBeVisible();
    const result = within(form.getByRole('region', { name: 'Test result' }));
    expect(result.getAllByRole('listitem').map(item => item.textContent)).toEqual([
      `${page}: 16 products in its data: 16 with no price`,
    ]);
    expect(previewSource).toHaveBeenLastCalledWith(expect.objectContaining({ kind: 'sitemap', page_url: page }));
  }, 30000);

  it('edits a source in place, including the settings of its kind', async () => {
    at('stores');
    const user = userEvent.setup();
    const settings = {
      sitemap_path: '/sitemap.xml', product_path_pattern: '-p/', free_shipping_marker: 'Help_FreeShipping',
    };
    const source: Source = {
      id: 'ghd', key: 'goharddrive', name: 'goHardDrive', kind: 'sitemap', base_url: 'https://www.goharddrive.com',
      settings, schedule: '0 3 * * *', enabled: true, transport: 'direct', basis: 'terms_allow', notes: 'No automated-access clause', next_run_at: null,
    };
    let attempts = 0;
    const updateSource = vi.fn<ListingsApi['updateSource']>(async (_id, input) => {
      attempts += 1;
      if (attempts === 1) throw new ApiValidationError({ 'settings.product_path_pattern': 'Enter a regular expression (missing ), unterminated subpattern).' });
      return { ...source, ...input };
    });
    renderApp({ listSources: async () => [source], updateSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: /^Edit/ }));
    const form = within(screen.getByRole('dialog', { name: 'Edit store' }));
    await user.click(form.getByRole('button', { name: 'Advanced' }));
    // The collector reads titles, store brands and which pages name a capacity for itself.
    for (const gone of ['Title prefix to remove', 'Own brands', 'Product code element class', 'Only product paths that name a capacity']) {
      expect(form.queryByLabelText(gone, { exact: true })).not.toBeInTheDocument();
    }
    const pattern = form.getByLabelText('Product path pattern', { exact: true });
    await user.clear(pattern);
    await user.type(pattern, '(-p/');
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(await form.findByText('Enter a regular expression (missing ), unterminated subpattern).')).toBeVisible();
    await user.clear(pattern);
    await user.type(pattern, '-p/');
    await user.clear(form.getByLabelText('Schedule (cron)', { exact: true }));
    await user.type(form.getByLabelText('Schedule (cron)', { exact: true }), '0 */8 * * *');
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(updateSource).toHaveBeenLastCalledWith('ghd', {
      name: 'goHardDrive', kind: 'sitemap', base_url: 'https://www.goharddrive.com', settings,
      schedule: '0 */8 * * *', enabled: true, transport: 'direct', basis: 'terms_allow', notes: 'No automated-access clause',
    });
  }, 20000);

  it('says where a store\'s pages carry several products as data', async () => {
    at('stores');
    const user = userEvent.setup();
    const addSource = vi.fn<ListingsApi['addSource']>(async input => ({
      ...input, id: 'seagate', key: 'seagate', next_run_at: null,
    }));
    renderApp({ listSources: async () => [], addSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: 'Add store' }));
    const form = within(screen.getByRole('dialog', { name: 'Add store' }));
    await user.type(form.getByLabelText('Name', { exact: true }), 'Seagate');
    await user.selectOptions(form.getByLabelText('Type', { exact: true }), 'sitemap');
    await user.type(form.getByLabelText('Store URL', { exact: true }), 'https://www.seagate.com');
    await user.click(form.getByRole('button', { name: 'Advanced' }));
    // Kept out of the way until a store needs them.
    expect(form.queryByLabelText('Data pattern', { exact: true })).not.toBeInTheDocument();
    await user.click(form.getByRole('button', { name: 'Pages that list several products' }));
    const typed: [string, string][] = [
      ['Data pattern', "models = JSON\\.parse\\('(.*?)'\\);"],
      ['Products path', '*.skus.*'],
      ['Model number field', 'modelNo'],
      ['Name field', 'name'],
      ['Price field', 'final_price'],
      ['Brand field', 'brand'],
      ['Stock field', 'stock_status'],
      ['In-stock value', 'IN_STOCK'],
    ];
    for (const [label, text] of typed) await user.type(form.getByLabelText(label, { exact: true }), text);
    await user.click(form.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(addSource).toHaveBeenCalledWith(expect.objectContaining({
      name: 'Seagate', kind: 'sitemap',
      settings: {
        data_pattern: "models = JSON\\.parse\\('(.*?)'\\);", data_items: '*.skus.*', data_model_field: 'modelNo',
        data_name_field: 'name', data_price_field: 'final_price', data_brand_field: 'brand', data_stock_field: 'stock_status', data_in_stock_value: 'IN_STOCK',
      },
    })));
  }, 30000);

  it('loads the sources once for the whole page: the Sources list, the filters and Add price share them', async () => {
    at('stores');
    const listSources = vi.fn<ListingsApi['listSources']>(async () => [makeSource('serverpartdeals', 'ServerPartDeals')]);
    renderApp({ listSources });
    const table = within(await screen.findByRole('table', { name: 'Stores' }));
    expect(await table.findByRole('row', { name: /ServerPartDeals/ })).toBeVisible();
    expect(listSources).toHaveBeenCalledTimes(1);
  });

  it('deletes a store from its edit form after confirming, and says why one is kept', async () => {
    at('stores');
    const user = userEvent.setup();
    let sources = [makeSource('trial', 'Trial Store'), makeSource('busy', 'Busy Store'), makeSource('other', 'Other', { kind: 'manual' })];
    const deleteSource = vi.fn<ListingsApi['deleteSource']>(async id => {
      if (id === 'busy') throw new Error('Offers are recorded under this source. Switch it off instead.');
      sources = sources.filter(source => source.id !== id);
    });
    renderApp({ listSources: async () => sources, deleteSource });
    const table = within(await screen.findByRole('table', { name: 'Stores' }));
    const names = () => table.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent);
    // Deleting is kept out of the rows, away from Run now and Edit.
    expect(table.queryByRole('button', { name: /Delete/ })).not.toBeInTheDocument();
    const deleteFromForm = async (name: string) => {
      await user.click(table.getByRole('button', { name: `Edit ${name}` }));
      await user.click(within(screen.getByRole('dialog', { name: 'Edit store' })).getByRole('button', { name: 'Delete store' }));
      return within(screen.getByRole('dialog', { name: 'Delete store' }));
    };
    // Other is always kept.
    await user.click(table.getByRole('button', { name: 'Edit Other' }));
    const other = within(screen.getByRole('dialog', { name: 'Edit store' }));
    expect(other.queryByRole('button', { name: 'Delete store' })).not.toBeInTheDocument();
    await user.click(other.getByRole('button', { name: 'Cancel' }));

    let dialog = await deleteFromForm('Trial Store');
    await user.click(dialog.getByRole('button', { name: 'Cancel' }));
    expect(deleteSource).not.toHaveBeenCalled();

    dialog = await deleteFromForm('Busy Store');
    await user.click(dialog.getByRole('button', { name: 'Delete' }));
    expect(await dialog.findByText('Offers are recorded under this source. Switch it off instead.')).toBeVisible();
    await user.click(dialog.getByRole('button', { name: 'Cancel' }));

    dialog = await deleteFromForm('Trial Store');
    expect(dialog.getByText('Delete Trial Store and its collector runs? This cannot be undone.')).toBeVisible();
    await user.click(dialog.getByRole('button', { name: 'Delete' }));
    expect(deleteSource).toHaveBeenLastCalledWith('trial');
    await waitFor(() => expect(names()).toEqual(['Busy Store', 'Other']));
  }, 20000);

  it('asks a source to run now, switched off or not, and shows when each is due', async () => {
    at('stores');
    const user = userEvent.setup();
    const source = (id: string, name: string, enabled: boolean, next_run_at: string | null): Source => ({
      id, key: id, name, kind: 'shopify', base_url: 'https://www.serverpartdeals.com',
      settings: { collections: ['hard-drives'] }, schedule: '0 3 * * *', enabled, transport: 'direct', basis: 'unconfirmed', notes: '', next_run_at,
    });
    let sources = [
      source('late', 'Late Store', true, '2026-09-22T03:00:00Z'),
      source('trial', 'Trial Store', false, null),
    ];
    const runSource = vi.fn<ListingsApi['runSource']>(async id => {
      sources = sources.map(entry => entry.id === id ? { ...entry, next_run_at: '2026-09-22T12:00:00Z' } : entry);
      return sources.find(entry => entry.id === id)!;
    });
    renderApp({ listSources: async () => sources, runSource });
    const table = within(await screen.findByRole('table', { name: 'Stores' }));
    const nextRuns = () => table.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[2].textContent);
    expect(nextRuns()).toEqual(['0 3 * * *Due now', '0 3 * * *Switched off']);
    await user.click(table.getByRole('button', { name: 'Run Trial Store now' }));
    expect(runSource).toHaveBeenCalledWith('trial');
    await waitFor(() => expect(nextRuns()).toEqual(['0 3 * * *Due now', '0 3 * * *Due now']));
    // Asking is answered where it can be seen, not only by a changed cell.
    expect(screen.getByRole('status')).toHaveTextContent('Trial Store goes next: the collector takes it once the store it is on is done.');
  }, 20000);

  it('edits the condition rules in order, and shows why one cannot be saved', async () => {
    at('stores');
    const user = userEvent.setup();
    let rules: ConditionRule[] = [
      { pattern: '\\brecertified\\b', condition: 'refurbished' },
      { pattern: '\\bnew\\b', condition: 'new' },
    ];
    const replaceConditionRules = vi.fn<ListingsApi['replaceConditionRules']>(async next => {
      if (next.some(rule => rule.pattern.startsWith('('))) {
        throw new ApiValidationError({ '0.pattern': 'Enter a regular expression (missing ), unterminated subpattern at position 0).' });
      }
      rules = next;
      return next;
    });
    renderApp({ listConditionRules: async () => rules, replaceConditionRules });
    const section = within(await screen.findByRole('region', { name: 'Condition rules' }));
    expect(await section.findByLabelText('Pattern 1')).toHaveValue('\\brecertified\\b');
    await user.click(section.getByRole('button', { name: 'Add rule' }));
    await user.type(section.getByLabelText('Pattern 3'), '(renewed');
    await user.selectOptions(section.getByLabelText('Condition 3'), 'refurbished');
    await user.click(section.getByRole('button', { name: 'Move rule 3 up' }));
    await user.click(section.getByRole('button', { name: 'Move rule 2 up' }));
    await user.click(section.getByRole('button', { name: 'Remove rule 3' }));
    await user.click(section.getByRole('button', { name: 'Save rules' }));
    expect(await section.findByText('Enter a regular expression (missing ), unterminated subpattern at position 0).')).toBeVisible();
    await user.clear(section.getByLabelText('Pattern 1'));
    await user.type(section.getByLabelText('Pattern 1'), '\\brenewed\\b');
    await user.click(section.getByRole('button', { name: 'Save rules' }));
    expect(replaceConditionRules).toHaveBeenLastCalledWith([
      { pattern: '\\brenewed\\b', condition: 'refurbished' },
      { pattern: '\\brecertified\\b', condition: 'refurbished' },
    ]);
    expect(await section.findByText('Condition rules saved.')).toBeVisible();
  }, 20000);

  it('edits which sitemap pages a SAP Commerce source reads', async () => {
    at('stores');
    const user = userEvent.setup();
    const settings = {
      api_url: 'https://api.westerndigital.com/wdwebservices/v2', site: 'us', sitemap_path: '/products-sitemap.xml',
      product_path_pattern: '^/products/internal-drives/', recertified_sku_prefix: 'R',
    };
    const source: Source = {
      id: 'wd', key: 'westerndigital', name: 'Western Digital', kind: 'sap_commerce',
      base_url: 'https://www.westerndigital.com', settings, schedule: '0 */8 * * *', enabled: true, transport: 'direct', basis: 'terms_allow', notes: '',
      next_run_at: null,
    };
    const updateSource = vi.fn<ListingsApi['updateSource']>(async (_id, input) => ({ ...source, ...input }));
    renderApp({ listSources: async () => [source], updateSource });
    const section = within(await screen.findByRole('region', { name: 'Stores' }));
    await user.click(await section.findByRole('button', { name: /^Edit/ }));
    const form = within(screen.getByRole('dialog', { name: 'Edit store' }));
    expect(form.queryByLabelText('Recertified path', { exact: true })).not.toBeInTheDocument();
    await user.click(form.getByRole('button', { name: 'Advanced' }));
    expect(form.getByLabelText('Sitemap path', { exact: true })).toHaveValue('/products-sitemap.xml');
    const pattern = form.getByLabelText('Product path pattern', { exact: true });
    await user.clear(pattern);
    await user.type(pattern, '^/products/(recertified/)?internal-drives/');
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(updateSource).toHaveBeenLastCalledWith('wd', expect.objectContaining({
      settings: { ...settings, product_path_pattern: '^/products/(recertified/)?internal-drives/' },
    }));
  }, 20000);

  it('shows the review queue a page at a time, as the API serves it', async () => {
    const user = userEvent.setup();
    const queue = Array.from({ length: 120 }, (_, index) => makeUnmatched(`queued-${index + 1}`));
    const listUnmatched = vi.fn(async () => queue);
    renderApp({ list: async () => catalogue(), listUnmatched });
    const review = within(await screen.findByRole('region', { name: /Needs matching/ }));
    const titles = () => review.getAllByRole('row').slice(1).map(row => within(row).getByRole('link').textContent);
    await waitFor(() => expect(titles()).toHaveLength(50));
    // The count is of the whole queue, not of the page.
    expect(screen.getByRole('heading', { name: 'Needs matching (120)' })).toBeVisible();
    const pages = within(review.getByRole('navigation', { name: 'Needs matching pages' }));
    expect(pages.getByText('1–50 of 120')).toBeVisible();
    expect(pages.getByRole('button', { name: 'Previous page' })).toBeDisabled();
    await user.click(pages.getByRole('button', { name: 'Next page' }));
    await waitFor(() => expect(titles()[0]).toBe('queued-51'));
    await user.click(pages.getByRole('button', { name: 'Next page' }));
    await waitFor(() => expect(titles()).toEqual(queue.slice(100).map(item => item.title)));
    expect(pages.getByText('101–120 of 120')).toBeVisible();
    expect(pages.getByRole('button', { name: 'Next page' })).toBeDisabled();
  }, 20000);

  it('steps back a page when the last offer on the last page is dealt with', async () => {
    const user = userEvent.setup();
    let queue = Array.from({ length: 51 }, (_, index) => makeUnmatched(`queued-${index + 1}`));
    const ignoreUnmatched = vi.fn<ListingsApi['ignoreUnmatched']>(async id => { queue = queue.filter(item => item.id !== id); });
    renderApp({ list: async () => catalogue(), listUnmatched: async () => queue, ignoreUnmatched });
    const review = within(await screen.findByRole('region', { name: /Needs matching/ }));
    await user.click(await review.findByRole('button', { name: 'Next page' }));
    await waitFor(() => expect(review.getAllByRole('row')).toHaveLength(2));
    await user.click(review.getByRole('button', { name: 'Ignore' }));
    await user.click(review.getByRole('button', { name: 'Yes, ignore' }));
    await waitFor(() => expect(review.getAllByRole('row')).toHaveLength(51));
    // One page is left: there is nowhere to go, but the page size can still be chosen.
    const pages = within(review.getByRole('navigation', { name: 'Needs matching pages' }));
    expect(pages.getByText('1–50 of 50')).toBeVisible();
    expect(pages.getByRole('button', { name: 'Previous page' })).toBeDisabled();
    expect(pages.getByRole('button', { name: 'Next page' })).toBeDisabled();
  }, 20000);

  it('shows the drives a page at a time, and a search starts again from the first page', async () => {
    at('drives');
    const user = userEvent.setup();
    const drives = Array.from({ length: 60 }, (_, index) => {
      const drive = makeDrive(`MPN${String(index + 1).padStart(3, '0')}`);
      return makeListing(`Drive ${String(index + 1).padStart(3, '0')}`, { drive, mpn: drive.mpn }, { price_per_tb: `${10 + index}.00` });
    });
    renderApp({ list: async () => drives });
    await screen.findByRole('table', { name: 'Drives' });
    expect(adminNames()).toHaveLength(50);
    const pages = within(screen.getByRole('navigation', { name: 'Drives pages' }));
    expect(pages.getByText('1–50 of 60')).toBeVisible();
    await user.click(pages.getByRole('button', { name: 'Next page' }));
    expect(adminNames()).toEqual(drives.slice(50).map(listing => listing.title));
    await user.type(screen.getByLabelText('Search drives', { exact: true }), 'Drive 00');
    expect(adminNames()).toEqual(drives.slice(0, 9).map(listing => listing.title));
    expect(screen.queryByRole('navigation', { name: 'Drives pages' })).not.toBeInTheDocument();
  }, 20000);

  it('shows as many rows per page as chosen for each list, remembered apart for the next visit', async () => {
    const user = userEvent.setup();
    const storage = memoryStorage();
    const drives = Array.from({ length: 60 }, (_, index) => {
      const drive = makeDrive(`MPN${String(index + 1).padStart(3, '0')}`);
      return makeListing(`Drive ${String(index + 1).padStart(3, '0')}`, { drive, mpn: drive.mpn }, { price_per_tb: `${10 + index}.00` });
    });
    const queue = Array.from({ length: 120 }, (_, index) => makeUnmatched(`queued-${index + 1}`));
    const api = { list: async () => drives, listUnmatched: async () => queue };
    const queued = () => within(screen.getByRole('region', { name: /Needs matching/ })).getAllByRole('row').length - 1;
    const tab = (name: RegExp) => user.click(within(screen.getByRole('navigation', { name: 'Admin sections' })).getByRole('link', { name }));
    const first = renderApp(api, '/', storage);
    await screen.findByRole('heading', { name: 'Admin' });
    await waitFor(() => expect(queued()).toBe(50));

    await tab(/Drives/);
    await user.selectOptions(screen.getByLabelText('Drives rows per page', { exact: true }), '25');
    expect(adminNames()).toHaveLength(25);
    expect(within(screen.getByRole('navigation', { name: 'Drives pages' })).getByText('1–25 of 60')).toBeVisible();
    // The offers to match keep their own size, and are fetched again at the one chosen for them.
    await tab(/To do/);
    expect(queued()).toBe(50);
    await user.selectOptions(screen.getByLabelText('Needs matching rows per page', { exact: true }), '100');
    await waitFor(() => expect(queued()).toBe(100));
    expect(within(screen.getByRole('navigation', { name: 'Needs matching pages' })).getByText('1–100 of 120')).toBeVisible();

    first.unmount();
    renderApp(api, '/', storage);
    await screen.findByRole('heading', { name: 'Admin' });
    await waitFor(() => expect(queued()).toBe(100));
    await tab(/Drives/);
    expect(adminNames()).toHaveLength(25);
    // With every drive on one page, the size can still be changed back.
    await user.selectOptions(screen.getByLabelText('Drives rows per page', { exact: true }), '100');
    expect(adminNames()).toHaveLength(60);
    expect(screen.getByLabelText('Drives rows per page', { exact: true })).toHaveValue('100');
  }, 30000);

  it('reviews scraped offers that could not be matched: resolving one and ignoring another', async () => {
    const user = userEvent.setup();
    let queue = [
      makeUnmatched('mystery', { title: 'Mystery 18TB drive', reason: 'missing_mpn' }),
      makeUnmatched('caddy', { title: 'Drive caddy', reason: 'missing_condition' }),
    ];
    let listings: ReturnType<typeof makeListing>[] = [];
    const resolveUnmatched = vi.fn<ListingsApi['resolveUnmatched']>(async (id, resolution) => {
      queue = queue.filter(item => item.id !== id);
      const offer = makeListing('Mystery 18TB drive', { mpn: resolution.mpn });
      listings = [offer];
      return offer;
    });
    const ignoreUnmatched = vi.fn<ListingsApi['ignoreUnmatched']>(async id => { queue = queue.filter(item => item.id !== id); });
    renderApp({ list: async () => listings, listUnmatched: async () => queue, resolveUnmatched, ignoreUnmatched });
    const review = within(await screen.findByRole('region', { name: /Needs matching/ }));
    const rows = (await review.findAllByRole('row')).slice(1);
    expect(within(rows[0]).getByText('No MPN found')).toBeVisible();
    expect(within(rows[1]).getByText('Condition not recognized')).toBeVisible();
    expect(within(rows[0]).getByRole('link', { name: 'Mystery 18TB drive' })).toHaveAttribute('href', queue[0].url);
    await user.click(within(rows[0]).getByRole('button', { name: 'Resolve' }));
    const form = within(screen.getByRole('dialog', { name: 'Resolve offer' }));
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST18000NM000J');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'manufacturer_recertified');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '18000');
    await user.click(form.getByRole('button', { name: 'Save' }));
    expect(resolveUnmatched).toHaveBeenCalledWith('mystery', { mpn: 'ST18000NM000J', condition: 'manufacturer_recertified', capacity_gb: 18000 });
    await waitFor(() => expect(review.getAllByRole('row')).toHaveLength(2));
    // Ignoring cannot be taken back here, so it asks first.
    const caddy = within(review.getAllByRole('row')[1]);
    await user.click(caddy.getByRole('button', { name: 'Ignore' }));
    await user.click(caddy.getByRole('button', { name: 'Keep' }));
    expect(ignoreUnmatched).not.toHaveBeenCalled();
    await user.click(caddy.getByRole('button', { name: 'Ignore' }));
    expect(caddy.getByText('Ignore this offer?')).toBeVisible();
    await user.click(caddy.getByRole('button', { name: 'Yes, ignore' }));
    expect(ignoreUnmatched).toHaveBeenCalledWith('caddy');
    expect(await review.findByText('Nothing to match.')).toBeVisible();
    await user.click(screen.getByRole('link', { name: 'Drives' }));
    expect(adminNames()).toEqual(['Mystery 18TB drive']);
  }, 15000);

  it('says the offers to match could not be loaded rather than that there are none, and loads them again on request', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    renderApp({ list: async () => catalogue(), listUnmatched: async () => {
      attempts += 1;
      if (attempts === 1) throw new Error('Unable to save or load listings (503).');
      return [makeUnmatched('waiting')];
    } });
    const review = within(await screen.findByRole('region', { name: /Needs matching/ }));
    expect(await review.findByRole('alert')).toHaveTextContent('The offers to match could not be loaded: Unable to save or load listings (503).');
    expect(review.queryByText('Nothing to match.')).not.toBeInTheDocument();
    await user.click(review.getByRole('button', { name: 'Try again' }));
    expect(await review.findByRole('link', { name: 'waiting' })).toBeVisible();
    expect(review.queryByRole('alert')).not.toBeInTheDocument();
  }, 15000);
});
