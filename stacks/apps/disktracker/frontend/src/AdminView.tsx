import { useCallback, useEffect, useState, type MouseEvent } from 'react';
import { Alert, Button, Table, Text, TextInput } from '@mantine/core';
import type { CollectorStatus, Run, DisktrackerApi, OfferSummary, Page, RecordedPrice, Source, ReviewFilter, ReviewItem } from './api';
import { ageLabel, driveIssues, elapsedLabel, endedBadly, issueLabel, issues, type Issue } from './admin-overview';
import { CollectorBand } from './CollectorBand';
import { DriveDetails } from './DriveDetails';
import { groupByDrive, groupKeyFor } from './drive-groups';
import { capacityLabel, driveName } from './listing-display';
import { defaultQuery, queryListings } from './listing-query';
import { Pager } from './Pager';
import { usePages, usePageSize } from './paging';
import { RecheckQueue } from './RecheckQueue';
import { SourcesSection } from './SourcesSection';
import { ConditionRulesSection } from './ConditionRulesSection';
import { ReviewQueue } from './ReviewQueue';
import { adminTabs, type AdminTab } from './view';

type Props = {
  api: DisktrackerApi; now: () => Date; nextId: () => string; recentDays: number;
  storage: Pick<Storage, 'getItem' | 'setItem'>;
  listings: OfferSummary[]; stores: Source[];
  /** Hand-entered offers overdue for a check, oldest first, as the server lists them. */
  toRecheck: OfferSummary[];
  /** Counts the app's changes: what the page loads itself is loaded again after each. */
  revision: number;
  /** The tab shown, and each tab's address and the way to it. */
  tab: AdminTab; tabHref: (tab: AdminTab) => string; onTab: (tab: AdminTab) => (event: MouseEvent) => void;
  /** The page of offers to match being shown, the way to its other pages, and why it could not be loaded. */
  queue: Page<ReviewItem>; queuePage: number; queueSize: number; queueError: string;
  /** Every offer waiting for review, however the queue is narrowed. */
  queueAll: number;
  onQueuePage: (page: number) => void; onQueueSize: (size: number) => void;
  queueFilter: ReviewFilter; onQueueFilter: (filter: ReviewFilter) => void;
  onRecorded: (listingId: string) => Promise<void>;
  onChanged: (notice?: string, recorded?: RecordedPrice) => Promise<void>;
};

const tabLabels: Record<AdminTab, string> = { todo: 'To do', stores: 'Stores', drives: 'Drives', rules: 'Condition rules' };
/** How often what the collector is doing is asked again while the page is open. */
const REFRESH_MS = 15_000;
const DAY_MS = 86_400_000;
/** A collector says something at least every minute or so; one silent for this long may be down. */
const QUIET_MS = 5 * 60_000;

/** What waits on a person (offers to recheck or match, collectors that failed), the stores and how
 * they are collected, and every drive to correct: one tab each. The tabs not shown stay as they
 * were left, so nothing typed in one is lost by looking at another. */
export function AdminView({ api, now, nextId, recentDays, storage, listings, toRecheck, revision, tab, tabHref, onTab, queue, queueAll, queuePage, queueSize, queueError, onQueuePage, onQueueSize, queueFilter, onQueueFilter, stores, onRecorded, onChanged }: Props) {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [runsError, setRunsError] = useState('');
  const [issue, setIssue] = useState<Issue | null>(null);
  const [search, setSearch] = useState('');
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [status, setStatus] = useState<CollectorStatus | null>(null);
  /** Every run of the last day, for the picture of them; without it the page still says how the last runs went. */
  const [recent, setRecent] = useState<Run[]>([]);
  const [runError, setRunError] = useState('');
  /** What the collector is doing and how its last runs went, asked again every so often: a run
   * starts, gets on and ends while the page is open. */
  const refresh = useCallback(async (active: () => boolean = () => true) => {
    await Promise.all([
      api.latestRuns().then(found => { if (active()) { setRuns(found); setRunsError(''); } })
        .catch(err => { if (active()) setRunsError(err instanceof Error ? err.message : 'Unknown error.'); }),
      // Without it the page still shows how the last runs went.
      api.collectorStatus().then(found => { if (active()) setStatus(found); }).catch(() => {}),
      api.recentRuns(new Date(now().getTime() - DAY_MS).toISOString()).then(found => { if (active()) setRecent(found); }).catch(() => {}),
    ]);
  }, [api, now]);
  useEffect(() => {
    let active = true;
    void refresh(() => active);
    const timer = setInterval(() => { void refresh(() => active); }, REFRESH_MS);
    return () => { active = false; clearInterval(timer); };
  }, [refresh]);
  const checkedAt = now();
  const storeLabel = (key: string) => stores.find(store => store.key === key)?.name ?? key;
  const waiting = toRecheck.length + queueAll;
  /** Last runs that did not complete, and are not still going. */
  const failed = (runs ?? []).filter(run => run.status !== 'completed' && run.status !== 'running');
  /** Runs that ended in failure, or were lost, rather than being stopped: these lead the page. */
  const broken = failed.filter(endedBadly);
  const runAgain = async (key: string) => {
    const source = stores.find(store => store.key === key);
    if (!source) return;
    try { await api.runSource(source.id); setRunError(''); await onChanged(`${source.name} is queued to run next.`); }
    catch (err) { setRunError(err instanceof Error ? err.message : 'The store could not be asked to run.'); }
  };
  const groups = groupByDrive(listings, 'unit-asc').map(group => ({ group, found: driveIssues(group, checkedAt, recentDays) }));
  const matching = new Set(queryListings(listings, { ...defaultQuery(), inStockOnly: false, search }, checkedAt, recentDays).map(groupKeyFor));
  const shown = groups.filter(({ group, found }) => matching.has(group.key) && (!issue || found.includes(issue)));
  const [drivesPerPage, setDrivesPerPage] = usePageSize(storage, 'drives');
  const pages = usePages(shown, drivesPerPage, `${search}\n${issue ?? ''}`);
  const selected = listings.filter(listing => groupKeyFor(listing) === selectedKey);
  return <>
    <h1>Admin</h1>
    <nav aria-label="Admin sections" className="tabs">
      {adminTabs.map(name => <a key={name} href={tabHref(name)} onClick={onTab(name)} aria-current={tab === name ? 'page' : undefined}>
        {tabLabels[name]}{name === 'todo' && waiting > 0 && ` (${waiting})`}</a>)}
    </nav>
    <div hidden={tab !== 'todo'}>
      {broken.length > 0 && <section aria-label="Failed runs" className="failures">
        {runError && <Alert color="red" role="alert" mb="sm">{runError}</Alert>}
        {broken.map(run => <div key={run.source} className="failure">
          <p><strong>{storeLabel(run.source)} {run.status === 'abandoned' ? 'was interrupted' : 'failed'} {ageLabel(checkedAt.getTime() - Date.parse(run.finished_at ?? run.updated_at))} ago.</strong>{' '}
            {run.reason && <><span className="failure-reason">{run.reason}</span>{' '}</>}
            <span>{run.seen} seen, {run.recorded} recorded, {run.queued} queued, {run.failed} failed, {run.rechecked} rechecked.</span>{' '}
            <a href={`${tabHref('stores')}#store-${run.source}`} onClick={event => {
              onTab('stores')(event);
              // To the store's own row, once the tab it is on is shown.
              setTimeout(() => document.getElementById(`store-${run.source}`)?.scrollIntoView?.({ block: 'center' }), 0);
            }}>See {storeLabel(run.source)}</a></p>
          <Button variant="default" aria-label={`Run ${storeLabel(run.source)} again`} onClick={() => { void runAgain(run.source); }}>Run again</Button>
        </div>)}
      </section>}
      <RecheckQueue offers={toRecheck} recentDays={recentDays} now={checkedAt} api={api} nextId={nextId} onChanged={onChanged} />
      <ReviewQueue items={queue.items} total={queue.total} all={queueAll} page={queuePage} pageSize={queueSize} onPage={onQueuePage} onPageSize={onQueueSize}
        filter={queueFilter} onFilter={onQueueFilter}
        stores={stores} error={queueError} onRetry={() => onQueuePage(queuePage)} api={api} onChanged={() => onChanged()} />
      <section aria-labelledby="collectors-heading" className="admin-section panel">
        <h2 id="collectors-heading">Collectors</h2>
        {status && (status.seen_at === null ? <Text size="sm" c="dimmed">No collector has been heard from yet.</Text>
          : checkedAt.getTime() - Date.parse(status.seen_at) > QUIET_MS
            && <Alert color="red" role="alert" mb="sm">The collector was last heard from {elapsedLabel(checkedAt.getTime() - Date.parse(status.seen_at))} ago. It may be down or restarting; a run shown as in progress may have ended with it.</Alert>)}
        {status?.running.map(run => <Text key={run.source} size="sm" className="running-now">
          <span className="status running" aria-hidden="true">● </span>Running now: <strong>{storeLabel(run.source)}</strong> for {elapsedLabel(checkedAt.getTime() - Date.parse(run.started_at))}, {run.seen} offer{run.seen === 1 ? '' : 's'} read so far.</Text>)}
        {status && status.waiting.length > 0 && <Text size="sm">Waiting: {status.waiting.map(storeLabel).join(', then ')}.</Text>}
        {status && status.seen_at !== null && status.running.length === 0 && status.waiting.length === 0
          && <Text size="sm" c="dimmed">Nothing is running or waiting to run.</Text>}
        {runsError && <Alert color="red" role="alert">Collector runs could not be loaded: {runsError}</Alert>}
        {runs !== null && (runs.length === 0 ? <Text size="sm" c="dimmed">No collector runs reported yet.</Text> : <>
          <Text size="sm" mt="sm">{failed.length === 0 ? `All ${runs.length} collectors finished their last run.`
            : `${runs.length - failed.length} of ${runs.length} collectors finished their last run.`}</Text>
          <a className="seller-link" href={tabHref('stores')} onClick={onTab('stores')}>See every store’s last run</a>
        </>)}
        <CollectorBand sources={stores.filter(store => store.kind !== 'manual')} runs={recent} status={status} now={checkedAt} />
      </section>
    </div>
    <div hidden={tab !== 'stores'}>
      <SourcesSection api={api} storage={storage} sources={stores} listings={listings} runs={runs} status={status} now={now}
        onChanged={async notice => { await Promise.all([onChanged(notice), refresh()]); }} />
    </div>
    <div hidden={tab !== 'rules'}>
      <ConditionRulesSection api={api} />
    </div>
    <div hidden={tab !== 'drives'}>
      <section aria-labelledby="drives-heading" className="admin-section">
        <h2 id="drives-heading">Drives</h2>
        <div className="drive-tools">
          <TextInput label="Search drives" aria-label="Search drives" placeholder="Name, MPN or store" w={360} maw="100%"
            value={search} onChange={event => setSearch(event.currentTarget.value)} />
          {issues.map(value => <button key={value} type="button" className="chip toggle" aria-pressed={issue === value}
            onClick={() => setIssue(issue === value ? null : value)}>
            {issueLabel(value)} ({groups.filter(({ found }) => found.includes(value)).length})</button>)}
        </div>
        <Text size="sm" c="dimmed" mb="xs">{shown.length} of {groups.length} drives{issue && ` · ${issueLabel(issue)}`}</Text>
        {groups.length === 0 ? <Text size="sm" c="dimmed">No drives yet.</Text> : <div className="sheet-scroll"><Table aria-label="Drives" verticalSpacing="sm">
          <Table.Thead><Table.Tr><Table.Th>Drive</Table.Th><Table.Th>MPN</Table.Th><Table.Th className="numeric">Capacity</Table.Th>
            <Table.Th className="numeric">Offers</Table.Th><Table.Th>Needs attention</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{pages.shown.map(({ group, found }) => <Table.Tr key={group.key} className="drive-row" onClick={() => setSelectedKey(group.key)}>
            <Table.Td><button type="button" className="drive-link" title={group.representative.title}>{driveName(group.drive)}</button></Table.Td>
            <Table.Td className="mono">{group.drive?.mpn ?? group.representative.mpn ?? '—'}</Table.Td>
            <Table.Td className="numeric">{capacityLabel(group.representative.capacity_gb)}</Table.Td>
            <Table.Td className="numeric">{group.listings.length}</Table.Td>
            <Table.Td className="secondary">{found.map(value => issueLabel(value)).join(', ') || '—'}</Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table></div>}
        <Pager label="Drives" page={pages.page} total={shown.length} pageSize={drivesPerPage} onPage={pages.setPage} onPageSize={setDrivesPerPage} />
      </section>
    </div>
    {selected.length > 0 && <DriveDetails api={api} now={now} nextId={nextId} driveKey={selectedKey!} title={selected[0].title} revision={revision} key={selectedKey} sort="unit-asc"
      knownCapacities={Object.fromEntries(listings.map(listing => [listing.mpn, listing.capacity_gb]))} manage besideTable={false} recentDays={recentDays} days={defaultQuery().days}
      onClose={() => setSelectedKey(null)} onRecorded={onRecorded} onChanged={onChanged} />}
  </>;
}
