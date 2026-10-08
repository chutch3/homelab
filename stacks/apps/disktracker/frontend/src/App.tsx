import { useCallback, useEffect, useState, type MouseEvent } from 'react';
import { Alert, Button, CloseButton, NativeSelect, Text } from '@mantine/core';
import type { Condition, ListingsApi, ListingSummary, Page, Source, UnmatchedItem } from './api';
import { AdminView } from './AdminView';
import { entryDefaults } from './entry-validation';
import { conditions } from './listing-display';
import { DriveDetails } from './DriveDetails';
import { DriveTable } from './DriveTable';
import { EntryForm } from './EntryForm';
import { ListingFilters } from './ListingFilters';
import { groupByDrive, groupKeyFor, knownDrives } from './drive-groups';
import { brandCounts, capacityCounts, conditionCounts, queryListings, priceLeaders, readQuery, sorts, writeQuery, queryErrors, type Sort } from './listing-query';
import { Pager } from './Pager';
import { usePages, usePageSize } from './paging';
import { overdueForRecheck } from './admin-overview';
import { adminTabAt, pathFor, viewAt, type AdminTab, type View } from './view';

/** base is the path the app is served under: / or a proxy prefix such as /absproxy/5173/. */
/** storage keeps small preferences between visits (localStorage in the browser). */
type Dependencies = {
  api: ListingsApi; base: string; storage: Pick<Storage, 'getItem' | 'setItem'>;
  now: () => Date; nextId: () => string; recentDays?: number;
};
const ENTRY_DEFAULTS = 'disktracker.entry-defaults';

export function App({ api, base, storage, now, nextId, recentDays = 7 }: Dependencies) {
  const [listings, setListings] = useState<ListingSummary[]>([]);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(true);
  /** The drive open in the panel, by its group key, and the condition it was opened on. */
  const [selected, setSelected] = useState<{ key: string; condition: Condition } | null>(null);
  const selectedKey = selected?.key ?? null;
  const [form, setForm] = useState(false);
  // A new form (and idempotency key) for each price entered back to back.
  const [formKey, setFormKey] = useState(0);
  const [previous, setPrevious] = useState<string>();
  /** What the last change did, said in a toast; listingId when it saved an offer, to show its drive. */
  const [notice, setNotice] = useState<{ text: string; listingId?: string } | null>(null);
  const [queue, setQueue] = useState<Page<UnmatchedItem>>({ items: [], total: 0 });
  const [queuePage, setQueuePage] = useState(0);
  const [queueSize, setQueueSize] = usePageSize(storage, 'review-queue');
  const [listingsPerPage, setListingsPerPage] = usePageSize(storage, 'listings');
  const [stores, setStores] = useState<Source[]>([]);
  const [view, setView] = useState<View>(() => viewAt(window.location.pathname, base));
  const [tab, setTab] = useState<AdminTab>(() => adminTabAt(window.location.pathname, base));
  const [queueError, setQueueError] = useState('');
  const [query, setQuery] = useState(() => readQuery(window.location.search));
  useEffect(() => {
    if (view !== 'listings') return;
    const search = writeQuery(query, window.location.search);
    window.history.replaceState(window.history.state, '', `${window.location.pathname}${search ? `?${search}` : ''}${window.location.hash}`);
  }, [query, view]);
  useEffect(() => {
    const restore = () => {
      setView(viewAt(window.location.pathname, base)); setTab(adminTabAt(window.location.pathname, base));
      setQuery(readQuery(window.location.search));
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
  const checkedAt = now();
  /** How much waits on a person: hand-entered offers to recheck, and offers to match. */
  const waiting = overdueForRecheck(listings, checkedAt, recentDays).length + queue.total;
  const visible = queryListings(listings, query, checkedAt, recentDays);
  const leaders = priceLeaders(visible, checkedAt, recentDays);
  const groups = groupByDrive(visible, query.sort);
  const pages = usePages(groups, listingsPerPage, JSON.stringify(query));
  /** The conditions a row's price may come from, as a phrase: "any condition", or those chosen. */
  const chosen = conditions.filter(option => query.conditions.includes(option.value)).map(option => option.label);
  const accepted = chosen.length === 0 ? 'any condition' : chosen.length === 1 ? chosen[0] : `${chosen.slice(0, -1).join(', ')} or ${chosen[chosen.length - 1]}`;
  const invalidFilters = Object.keys(queryErrors(query)).length > 0;
  const selectedSummaries = listings.filter(listing => groupKeyFor(listing) === selectedKey);
  const knownCapacities = Object.fromEntries(listings.map(listing => [listing.mpn, listing.capacity_gb]));
  const savedListing = view === 'listings' ? listings.find(listing => listing.id === notice?.listingId) : undefined;
  async function reload(listingId: string) {
    const result = await api.list();
    setListings(result); setError('');
    setNotice({ text: `Saved ${result.find(listing => listing.id === listingId)?.title ?? 'the price'}.`, listingId });
  }
  /** Reload after a change; a message replaces the current one, none leaves it. */
  /** A page of the review queue; one left empty by its offers being dealt with gives way to the page before it. */
  async function queueAt(page: number, size: number): Promise<{ page: number; found: Page<UnmatchedItem> }> {
    const found = await api.listUnmatched({ limit: size, offset: page * size });
    return found.items.length === 0 && page > 0 ? queueAt(page - 1, size) : { page, found };
  }
  async function showQueue(page: number, size = queueSize) {
    try {
      const shown = await queueAt(page, size);
      setQueue(shown.found); setQueuePage(shown.page); setQueueError('');
    } catch (err) { setQueueError(err instanceof Error ? err.message : 'Unknown error.'); }
  }
  async function reloadAfterChange(message?: string) {
    const [, result, found] = await Promise.all([showQueue(queuePage), api.list(), api.listSources()]);
    setListings(result); setStores(found); setError('');
    if (message !== undefined) setNotice({ text: message });
  }
  /** The drives, loaded when the app opens and again when a failed load is retried. */
  const load = useCallback((active: () => boolean = () => true) => {
    setLoading(true); setLoadError('');
    return api.list().then(data => { if (active()) setListings(data); }).catch(err => { if (active()) setLoadError(err.message); })
      .finally(() => { if (active()) setLoading(false); });
  }, [api]);
  const addOffer = () => { setPrevious(undefined); setForm(true); };
  useEffect(() => {
    let active = true;
    void load(() => active);
    api.listUnmatched({ limit: queueSize, offset: 0 }).then(found => { if (active) setQueue(found); })
      .catch(err => { if (active) setQueueError(err instanceof Error ? err.message : 'Unknown error.'); });
    api.listSources().then(found => { if (active) setStores(found); }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
    // The queue's page size is read once here; changing it fetches the queue again itself.
  }, [api, load]);
  const loadingNote = <div role="status" className="loading"><span className="visually-hidden">Loading drives…</span>
    {Array.from({ length: 6 }, (_, index) => <div key={index} className="skeleton-row" aria-hidden="true" />)}</div>;
  const loadAlert = loadError && <Alert color="red" role="alert" mb="md" title="The drives could not be loaded">
    <Text size="sm" mb="sm">{loadError}</Text><Button variant="default" onClick={() => { void load(); }}>Try again</Button></Alert>;
  return <>
    <header className="site-header"><strong className="wordmark"><span className="mark" aria-hidden="true" />disktracker</strong>
      <nav aria-label="Pages" className="site-nav">
        {(['listings', 'admin'] as const).map(page => <a key={page} href={pathFor(page, base)} onClick={go(page)}
          aria-current={view === page ? 'page' : undefined}>{page === 'listings' ? 'Prices' : 'Admin'}
          {page === 'admin' && waiting > 0 && <span className="nav-count" aria-label={`${waiting} to do`}>{waiting}</span>}</a>)}
      </nav>
      <span className="market">US / USD</span>
      <Button onClick={addOffer}>Add offer</Button></header>
    {view === 'admin' ? <main>
      {error && <Alert color="red" role="alert" mb="md">{error}</Alert>}
      {loading ? loadingNote : loadAlert || <AdminView api={api} now={now} nextId={nextId} recentDays={recentDays} storage={storage} listings={listings}
          tab={tab} tabHref={name => pathFor('admin', base, name)} onTab={name => go('admin', name)}
          queue={queue} queuePage={queuePage} queueSize={queueSize} queueError={queueError}
          onQueuePage={page => { void showQueue(page); }} onQueueSize={size => { setQueueSize(size); void showQueue(0, size); }} stores={stores}
          onRecorded={reload} onChanged={reloadAfterChange} />}
    </main> : <main>
      <h1 className="visually-hidden">Prices</h1>
      <ListingFilters query={query} onChange={setQuery} recentDays={recentDays} stores={stores} capacities={capacityCounts(listings)} brands={brandCounts(listings)} conditions={conditionCounts(listings)} />
      {error && <Alert color="red" role="alert" mb="md">{error}</Alert>}
      {loading ? loadingNote : loadAlert || <>
        <div className="results-status" aria-live="polite"><Text size="sm" fw={600}>{groups.length} drive{groups.length === 1 ? '' : 's'} · {visible.length} offer{visible.length === 1 ? '' : 's'}</Text>
          {visible.length > 0 && <Text size="xs" c="dimmed">Each drive shows its lowest price in {accepted} · totals include shipping and fees, before tax</Text>}
        </div>
        <NativeSelect className="mobile-sort" label="Sort by" aria-label="Sort by" data={[...sorts]} value={query.sort}
          onChange={event => setQuery({ ...query, sort: event.currentTarget.value as Sort })} />
        {invalidFilters ? <div className="empty">Check the filter values above.</div>
          : visible.length === 0 ? <div className="empty">{listings.length ? 'No drives match these filters.'
            : <><p>No drives yet.</p><Button onClick={addOffer}>Add your first offer</Button></>}</div>
          : <DriveTable groups={pages.shown} sort={query.sort} onSort={sort => setQuery({ ...query, sort })}
              onSelect={(key, condition) => setSelected({ key, condition })} now={checkedAt} recentDays={recentDays} leaders={leaders} />}
        {!invalidFilters && <Pager label="Drives" page={pages.page} total={groups.length} pageSize={listingsPerPage} onPage={pages.setPage} onPageSize={setListingsPerPage} />}
      </>}
      {selectedSummaries.length > 0 && <DriveDetails api={api} now={now} nextId={nextId} listings={listings} driveKey={selectedKey!} key={selectedKey}
        condition={selected!.condition} sort={query.sort} knownCapacities={knownCapacities} manage={false} onClose={() => setSelected(null)}
        onRecorded={reload} onChanged={reloadAfterChange} />}
    </main>}
    {form && <EntryForm key={formKey} previous={previous}
      onAnother={title => { setPrevious(title); setFormKey(key => key + 1); }} knownCapacities={knownCapacities} knownDrives={knownDrives(listings)} api={api} now={now} nextId={nextId} listing={null} stores={stores}
      defaults={entryDefaults(storage.getItem(ENTRY_DEFAULTS), stores)} onEntered={defaults => storage.setItem(ENTRY_DEFAULTS, JSON.stringify(defaults))}
      onClose={() => setForm(false)} onSaved={reload} />}
    {notice && <div className="toast">
      <div role="status"><span>{notice.text}</span>
        {savedListing && !visible.some(listing => listing.id === savedListing.id) && <span>It is hidden by your filters.</span>}</div>
      {savedListing && <Button variant="white" onClick={() => setSelected({ key: groupKeyFor(savedListing), condition: savedListing.condition })}>Show drive</Button>}
      <CloseButton aria-label="Dismiss message" variant="transparent" c="white" onClick={() => setNotice(null)} />
    </div>}
  </>;
}
