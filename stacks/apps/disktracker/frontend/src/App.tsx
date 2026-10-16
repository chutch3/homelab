import { useCallback, useEffect, useMemo, useState, type MouseEvent } from 'react';
import { Alert, Button, CloseButton, NativeSelect, Text } from '@mantine/core';
import type { Condition, DisktrackerApi, DrivePage, DriveQuery, DriveScope, OfferSummary, Page, PriceMark, PriceRange, Source, ReviewFilter, ReviewItem, RecordedPrice } from './api';
import { AdminView } from './AdminView';
import { entryDefaults } from './entry-validation';
import { conditions } from './listing-display';
import { DriveDetails, driveIdOf } from './DriveDetails';
import { DriveTable } from './DriveTable';
import { EntryForm } from './EntryForm';
import { ListingFilters } from './ListingFilters';
import { groupKeyFor, knownDrives, type DriveGroup } from './drive-groups';
import { periods, readQuery, scopeOf, scopeSearch, sorts, writeQuery, queryErrors, type ListingQuery, type Period, type Sort } from './listing-query';
import { Pager } from './Pager';
import { usePageSize } from './paging';
import { DriveRail } from './DriveRail';
import { rail as buildRail } from './rail-marks';
import { TrendsView } from './TrendsView';
import { adminTabAt, pathFor, readTrendQuery, viewAt, writeTrendQuery, type AdminTab, type TrendQuery, type View } from './view';

/** base is the path the app is served under: / or a proxy prefix such as /absproxy/5173/. */
/** storage keeps small preferences between visits (localStorage in the browser). */
type Dependencies = {
  api: DisktrackerApi; base: string; storage: Pick<Storage, 'getItem' | 'setItem'>;
  now: () => Date; nextId: () => string; recentDays?: number;
};
const ENTRY_DEFAULTS = 'disktracker.entry-defaults';

/** The drive query the server takes for the app's filters, a page of the list. */
export function driveQuery(query: ListingQuery, recentDays: number, page: number, size: number): DriveQuery {
  const total = query.maxTotal.trim();
  return {
    ...scopeOf(query),
    ...(total ? { max_total_cents: Math.round(Number(total) * 100) } : {}),
    ...(query.inStockOnly ? {} : { in_stock: false }),
    ...(query.recentOnly ? { recent_only: true } : {}),
    recent_days: recentDays, sort: query.sort, range_days: query.days, limit: size, offset: page * size,
  };
}

export function App({ api, base, storage, now, nextId, recentDays = 7 }: Dependencies) {
  /** Every offer, for what manages them (the Admin page, the entry form): loaded only where they are wanted. */
  const [listings, setListings] = useState<OfferSummary[]>([]);
  const [listingsLoaded, setListingsLoaded] = useState(false);
  /** The page of drives the Prices page shows, as the server worked it out. */
  const [drivesPage, setDrivesPage] = useState<DrivePage | null>(null);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');
  /** Counts changes made here: what was loaded is loaded again after each. */
  const [revision, setRevision] = useState(0);
  /** The drive open in the panel, by its group key, the condition it was opened on, and its name until it loads. */
  const [selected, setSelected] = useState<{ key: string; condition: Condition; title: string } | null>(null);
  const selectedKey = selected?.key ?? null;
  const [form, setForm] = useState(false);
  // A new form (and idempotency key) for each price entered back to back.
  const [formKey, setFormKey] = useState(0);
  const [previous, setPrevious] = useState<string>();
  /** What the last change did, said in a toast; the drive of the offer it saved, to show it, and whether the filters hide it. */
  const [notice, setNotice] = useState<{ text: string; saved?: { key: string; condition: Condition; title: string; hidden: boolean }; recorded?: RecordedPrice } | null>(null);
  const [queue, setQueue] = useState<Page<ReviewItem>>({ items: [], total: 0 });
  const [queuePage, setQueuePage] = useState(0);
  const [queueFilter, setQueueFilter] = useState<ReviewFilter>({});
  /** Every offer waiting for review, however the queue is narrowed. */
  const [queueAll, setQueueAll] = useState(0);
  const [queueSize, setQueueSize] = usePageSize(storage, 'review-queue');
  const [listingsPerPage, setListingsPerPage] = usePageSize(storage, 'listings');
  const [stores, setStores] = useState<Source[]>([]);
  const [overdue, setOverdue] = useState<OfferSummary[]>([]);
  const [marks, setMarks] = useState<PriceMark[] | null>(null);
  const [view, setView] = useState<View>(() => viewAt(window.location.pathname, base));
  const [tab, setTab] = useState<AdminTab>(() => adminTabAt(window.location.pathname, base));
  const [queueError, setQueueError] = useState('');
  const [query, setQuery] = useState(() => readQuery(window.location.search));
  const [trendQuery, setTrendQuery] = useState<TrendQuery>(() => readTrendQuery(window.location.search));
  // The trends page keeps its period and split in the URL, as the prices page keeps its filters.
  useEffect(() => {
    if (view !== 'trends') return;
    const search = writeTrendQuery(trendQuery);
    window.history.replaceState(window.history.state, '', `${window.location.pathname}${search ? `?${search}` : ''}`);
  }, [trendQuery, view]);
  useEffect(() => {
    if (view !== 'listings') return;
    const search = writeQuery(query, window.location.search);
    window.history.replaceState(window.history.state, '', `${window.location.pathname}${search ? `?${search}` : ''}${window.location.hash}`);
  }, [query, view]);
  useEffect(() => {
    const restore = () => {
      setView(viewAt(window.location.pathname, base)); setTab(adminTabAt(window.location.pathname, base));
      setQuery(readQuery(window.location.search)); setTrendQuery(readTrendQuery(window.location.search));
    };
    window.addEventListener('popstate', restore);
    return () => window.removeEventListener('popstate', restore);
  }, [base]);
  const go = (next: View, nextTab: AdminTab = 'todo') => (event: MouseEvent) => {
    event.preventDefault();
    const search = next === 'listings' ? writeQuery(query, '') : '';
    window.history.pushState(null, '', `${pathFor(next, base, nextTab)}${search ? `?${search}` : ''}`);
    setView(next); setTab(nextTab); setSelected(null); setNotice(null);
  };
  // A change of filter, order or page size starts again from the first page; how far back the ranges look does not.
  const scope = `${listingsPerPage}\n${JSON.stringify({ ...query, days: null })}`;
  const [at, setAt] = useState({ page: 0, scope });
  const page = at.scope === scope ? at.page : 0;
  const setPage = (next: number) => setAt({ page: next, scope });
  const invalidFilters = Object.keys(queryErrors(query)).length > 0;
  const asked = JSON.stringify(driveQuery(query, recentDays, page, listingsPerPage));
  /** The page of drives, asked for when the filters, the page or anything recorded changes. */
  const loadDrives = useCallback((active: () => boolean = () => true) => {
    if (invalidFilters) return Promise.resolve();
    setLoadError('');
    return api.drives(JSON.parse(asked) as DriveQuery).then(found => {
      if (!active()) return;
      // A page left empty by its drives going away gives way to the last page there is.
      if (!found.items.length && found.offset > 0 && found.total > 0) { setPage(Math.ceil(found.total / found.limit) - 1); return; }
      setDrivesPage(found);
    }).catch(err => { if (active()) setLoadError(err instanceof Error ? err.message : 'Unknown error.'); });
  }, [api, asked, invalidFilters]);
  useEffect(() => {
    if (view !== 'listings') return;
    let active = true;
    void loadDrives(() => active);
    return () => { active = false; };
  }, [view, loadDrives, revision]);
  // Every offer, where they are managed: on the Admin page, and by the entry form, for the drives it knows.
  const wantsListings = view === 'admin' || form;
  useEffect(() => {
    if (!wantsListings) return;
    let active = true;
    api.listOffers().then(found => { if (active) { setListings(found); setListingsLoaded(true); } })
      .catch(err => { if (active) setLoadError(err instanceof Error ? err.message : 'Unknown error.'); });
    return () => { active = false; };
  }, [api, wantsListings, revision]);
  // What waits on a person, counted on every page: offers entered by hand that are due a check.
  useEffect(() => {
    let active = true;
    api.offersToRecheck(recentDays).then(found => { if (active) setOverdue(found); }).catch(() => {});
    return () => { active = false; };
  }, [api, recentDays, revision]);
  // What the drives Trends follows cost today: a report, not the page of drives on show.
  const trendScope = useMemo(() => JSON.stringify(scopeOf(trendQuery.scope)), [trendQuery.scope]);
  useEffect(() => {
    if (view !== 'trends') return;
    let active = true;
    api.pricesToday(recentDays, JSON.parse(trendScope) as DriveScope).then(found => { if (active) setMarks(found); }).catch(() => {});
    return () => { active = false; };
  }, [api, view, recentDays, revision, trendScope]);
  /** When the page was worked out: the moment its prices are judged recent or stale against. */
  const checkedAt = useMemo(() => drivesPage ? new Date(drivesPage.as_of) : now(), [drivesPage]);
  /** How much waits on a person: hand-entered offers to recheck, and offers to match. */
  const waiting = overdue.length + queueAll;
  const groups: DriveGroup[] = (drivesPage?.items ?? []).map(row => ({ key: row.key, drive: row.drive, listings: row.offers, representative: row.representative }));
  const leaders = { total: new Set(drivesPage?.lowest.total ?? []), unit: new Set(drivesPage?.lowest.unit ?? []) };
  const ranges: Record<string, PriceRange> = Object.fromEntries((drivesPage?.items ?? []).flatMap(row => row.range ? [[row.key, row.range]] : []));
  const options = drivesPage?.filter_options ?? { brands: [], capacities: [], conditions: [] };
  /** Whether there are any drives at all, whatever the filters: every drive has a capacity. */
  const anyDrives = options.capacities.length > 0;
  const known = useMemo(() => ({
    capacityOf: Object.fromEntries(listings.map(listing => [listing.mpn, listing.capacity_gb])), drives: knownDrives(listings),
  }), [listings]);
  const rail = useMemo(() => buildRail((marks ?? []).map(mark => ({
    key: `drive:${mark.drive_id}`, condition: mark.condition, title: mark.title, capacityGb: mark.capacity_gb, perTb: mark.per_tb_cents, lowest: mark.lowest,
  }))), [marks]);
  /** The conditions a row's price may come from, as a phrase: "any condition", or those chosen. */
  const chosen = conditions.filter(option => query.conditions.includes(option.value)).map(option => option.label);
  const accepted = chosen.length === 0 ? 'any condition' : chosen.length === 1 ? chosen[0] : `${chosen.slice(0, -1).join(', ')} or ${chosen[chosen.length - 1]}`;
  const knownCapacities = known.capacityOf;
  const total = drivesPage?.total ?? 0, offerCount = drivesPage?.offers ?? 0, soldOut = drivesPage?.sold_out ?? 0;
  /** Reload after saving a price: say what was saved, and whether the filters hide its drive. */
  async function reload(offerId: string) {
    setRevision(count => count + 1); setError('');
    try {
      const offer = await api.offer(offerId);
      const key = groupKeyFor(offer);
      const shown = await api.drives({ ...driveQuery(query, recentDays, 0, 1), drive_id: driveIdOf(key) });
      setNotice({ text: `Saved ${offer.title}.`, saved: { key, condition: offer.condition, title: offer.title, hidden: shown.total === 0 } });
    } catch {
      // The price is saved whatever else could not be read: saying so is enough.
      setNotice({ text: 'Saved the price.' });
    }
  }
  /** Reload after a change; a message replaces the current one, none leaves it. */
  /** A page of the review queue; one left empty by its offers being dealt with gives way to the page before it. */
  async function queueAt(page: number, size: number, filter: ReviewFilter): Promise<{ page: number; found: Page<ReviewItem> }> {
    const found = await api.reviewItems({ limit: size, offset: page * size, ...filter });
    return found.items.length === 0 && page > 0 ? queueAt(page - 1, size, filter) : { page, found };
  }
  async function showQueue(page: number, size = queueSize, filter = queueFilter) {
    try {
      const shown = await queueAt(page, size, filter);
      const narrowed = filter.store !== undefined || filter.reason !== undefined;
      const all = narrowed ? (await api.reviewItems({ limit: 1, offset: 0 })).total : shown.found.total;
      setQueue(shown.found); setQueuePage(shown.page); setQueueAll(all); setQueueError('');
    } catch (err) { setQueueError(err instanceof Error ? err.message : 'Unknown error.'); }
  }
  /** Reload after a change; a message replaces the current one, none leaves it. */
  async function reloadAfterChange(message?: string, recorded?: RecordedPrice) {
    setRevision(count => count + 1);
    const [, found] = await Promise.all([showQueue(queuePage), api.listSources()]);
    setStores(found); setError('');
    if (message !== undefined) setNotice({ text: message, recorded });
  }
  const addOffer = () => { setPrevious(undefined); setForm(true); };
  useEffect(() => {
    let active = true;
    api.reviewItems({ limit: queueSize, offset: 0 }).then(found => { if (active) { setQueue(found); setQueueAll(found.total); } })
      .catch(err => { if (active) setQueueError(err instanceof Error ? err.message : 'Unknown error.'); });
    api.listSources().then(found => { if (active) setStores(found); }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
    // The queue's page size is read once here; changing it fetches the queue again itself.
  }, [api]);
  const loading = view === 'admin' ? !listingsLoaded && !loadError : drivesPage === null && !loadError && !invalidFilters;
  const loadingNote = <div role="status" className="loading"><span className="visually-hidden">Loading drives…</span>
    {Array.from({ length: 6 }, (_, index) => <div key={index} className="skeleton-row" aria-hidden="true" />)}</div>;
  const loadAlert = loadError && <Alert color="red" role="alert" mb="md" title="The drives could not be loaded">
    <Text size="sm" mb="sm">{loadError}</Text><Button variant="default" onClick={() => setRevision(count => count + 1)}>Try again</Button></Alert>;
  return <>
    <header className="site-header"><strong className="wordmark">disktracker</strong>
      <nav aria-label="Pages" className="site-nav">
        {(['listings', 'trends', 'admin'] as const).map(page => <a key={page} href={pathFor(page, base)} onClick={go(page)}
          aria-current={view === page ? 'page' : undefined}>{{ listings: 'Prices', trends: 'Trends', admin: 'Admin' }[page]}
          {page === 'admin' && waiting > 0 && <span className="nav-count" aria-label={`${waiting} to do`}>{waiting}</span>}</a>)}
      </nav>
      <span className="market">US / USD</span>
      <Button variant="default" onClick={addOffer}>Record price</Button></header>
    {view === 'trends' ? <main>
      <TrendsView api={api} base={base} recentDays={recentDays} stores={stores} query={trendQuery} onChange={setTrendQuery} now={now} />
      {/* A mark opens its drive where drives are opened: on the prices page. */}
      {marks !== null && <DriveRail rail={rail} onSelect={(key, condition) => {
        window.history.pushState(null, '', pathFor('listings', base));
        const title = marks.find(mark => `drive:${mark.drive_id}` === key)?.title ?? '';
        setView('listings'); setSelected({ key, condition, title });
      }} />}
    </main> : view === 'admin' ? <main>
      {error && <Alert color="red" role="alert" mb="md">{error}</Alert>}
      {loading ? loadingNote : loadAlert || <AdminView api={api} now={now} nextId={nextId} recentDays={recentDays} storage={storage} listings={listings} toRecheck={overdue} revision={revision}
          tab={tab} tabHref={name => pathFor('admin', base, name)} onTab={name => go('admin', name)}
          queue={queue} queueAll={queueAll} queuePage={queuePage} queueSize={queueSize} queueError={queueError}
          queueFilter={queueFilter} onQueueFilter={filter => { setQueueFilter(filter); void showQueue(0, queueSize, filter); }}
          onQueuePage={page => { void showQueue(page); }} onQueueSize={size => { setQueueSize(size); void showQueue(0, size); }} stores={stores}
          onRecorded={reload} onChanged={reloadAfterChange} />}
    </main> : <main>
      <h1 className="visually-hidden">Prices</h1>
      <div className="listing-layout"><div className="listing-main">
      <ListingFilters query={query} onChange={setQuery} recentDays={recentDays} stores={stores} capacities={options.capacities.map(({ value, drives }) => ({ capacity_gb: value, drives }))}
        brands={options.brands.map(({ value, drives }) => ({ brand: value, drives }))}
        conditions={options.conditions.map(({ value, drives }) => ({ condition: value, drives }))} />
      {error && <Alert color="red" role="alert" mb="md">{error}</Alert>}
      {loading ? loadingNote : loadAlert || <>
        <div className="results-status" aria-live="polite"><Text size="sm" fw={600}>{total} drive{total === 1 ? '' : 's'}, {offerCount} offer{offerCount === 1 ? '' : 's'}</Text>
          {soldOut > 0 && <Text size="xs" c="dimmed"><span>{soldOut} out of stock hidden.</span> <button type="button" className="text-button" onClick={() => setQuery({ ...query, inStockOnly: false })}>Show</button></Text>}
          {offerCount > 0 && <Text size="xs" c="dimmed">Lowest price per drive{chosen.length > 0 && `, ${accepted}`}. $/TB and totals include shipping, before tax.</Text>}
          {scopeSearch(query) && <a className="seller-link" href={`${pathFor('trends', base)}?${scopeSearch(query)}`}>Trends for these drives</a>}
        </div>
        {/* On a phone, where the table's own headings are not shown: its order and period, side by side. */}
        <div className="mobile-sorts">
        <NativeSelect className="mobile-sort" label="Sort by" aria-label="Sort by" data={[...sorts]} value={query.sort}
          onChange={event => setQuery({ ...query, sort: event.currentTarget.value as Sort })} />
        <NativeSelect className="mobile-sort" label="Compare with the last" aria-label="Compare with the last" value={String(query.days)}
          data={periods.map(days => ({ value: String(days), label: `${days} days` }))} onChange={event => setQuery({ ...query, days: Number(event.currentTarget.value) as Period })} />
        </div>
        {invalidFilters ? <div className="empty">Check the filter values above.</div>
          : total === 0 ? <div className="empty">{anyDrives ? 'No drives match these filters.'
            : <><p>No drives yet.</p><Button onClick={addOffer}>Record your first price</Button></>}</div>
          : <DriveTable groups={groups} sort={query.sort} onSort={sort => setQuery({ ...query, sort })}
              onSelect={(key, condition) => setSelected({ key, condition, title: groups.find(group => group.key === key)?.representative.title ?? '' })} now={checkedAt} recentDays={recentDays} leaders={leaders} ranges={ranges} rangeDays={query.days} onRangeDays={days => setQuery({ ...query, days })} />}
        {!invalidFilters && <Pager label="Drives" page={page} total={total} pageSize={listingsPerPage} onPage={setPage} onPageSize={setListingsPerPage} />}
      </>}
      </div>
      {selected && <DriveDetails api={api} now={now} nextId={nextId} driveKey={selectedKey!} title={selected.title} revision={revision} key={selectedKey}
        condition={selected!.condition} sort={query.sort} knownCapacities={knownCapacities} manage={false} besideTable recentDays={recentDays} days={query.days} onClose={() => setSelected(null)}
        onRecorded={reload} onChanged={reloadAfterChange} />}
      </div>
    </main>}
    {form && <EntryForm key={formKey} previous={previous}
      onAnother={title => { setPrevious(title); setFormKey(key => key + 1); }} knownCapacities={knownCapacities} knownDrives={known.drives} api={api} now={now} nextId={nextId} listing={null} stores={stores}
      defaults={entryDefaults(storage.getItem(ENTRY_DEFAULTS), stores)} onEntered={defaults => storage.setItem(ENTRY_DEFAULTS, JSON.stringify(defaults))}
      onClose={() => setForm(false)} onSaved={reload} />}
    {notice && <div className="toast">
      <div role="status"><span>{notice.text}</span>
        {view === 'listings' && notice.saved?.hidden && <span>It is hidden by your filters.</span>}</div>
      {view === 'listings' && notice.saved && <Button variant="white" onClick={() => setSelected(notice.saved!)}>Show drive</Button>}
      {/* A price just recorded can be taken back while its message is up: a mistyped one need not stand. */}
      {notice.recorded && <Button variant="white" onClick={async () => {
        const { priceId } = notice.recorded!;
        try { await api.deletePrice(priceId); await reloadAfterChange('Undone.'); }
        catch (err) { setError(err instanceof Error ? err.message : 'The price could not be taken back.'); }
      }}>Undo</Button>}
      <CloseButton aria-label="Dismiss message" variant="transparent" c="white" onClick={() => setNotice(null)} />
    </div>}
  </>;
}
