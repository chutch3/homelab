import { useCallback, useEffect, useState, type MouseEvent } from 'react';
import { Alert, Table, Text, TextInput } from '@mantine/core';
import type { CollectorRun, CollectorStatus, ListingsApi, ListingSummary, Page, Source, UnmatchedItem } from './api';
import { driveIssues, elapsedLabel, issueLabel, issues, overdueForRecheck, type Issue } from './admin-overview';
import { DriveDetails } from './DriveDetails';
import { groupByDrive, groupKeyFor } from './drive-groups';
import { capacityLabel } from './listing-display';
import { defaultQuery, queryListings } from './listing-query';
import { Pager } from './Pager';
import { usePages, usePageSize } from './paging';
import { RecheckQueue } from './RecheckQueue';
import { SourcesSection } from './SourcesSection';
import { ConditionRulesSection } from './ConditionRulesSection';
import { ReviewQueue } from './ReviewQueue';
import { adminTabs, type AdminTab } from './view';

type Props = {
  api: ListingsApi; now: () => Date; nextId: () => string; recentDays: number;
  storage: Pick<Storage, 'getItem' | 'setItem'>;
  listings: ListingSummary[]; stores: Source[];
  /** The tab shown, and each tab's address and the way to it. */
  tab: AdminTab; tabHref: (tab: AdminTab) => string; onTab: (tab: AdminTab) => (event: MouseEvent) => void;
  /** The page of offers to match being shown, the way to its other pages, and why it could not be loaded. */
  queue: Page<UnmatchedItem>; queuePage: number; queueSize: number; queueError: string;
  onQueuePage: (page: number) => void; onQueueSize: (size: number) => void;
  onRecorded: (listingId: string, observedAt: string) => Promise<void>;
  onChanged: (notice?: string) => Promise<void>;
};

const dateLabel = (value: string) => new Date(value).toLocaleString();
const tabLabels: Record<AdminTab, string> = { todo: 'To do', stores: 'Stores', drives: 'Drives' };
/** How often what the collector is doing is asked again while the page is open. */
const REFRESH_MS = 15_000;
/** A collector says something at least every minute or so; one silent for this long may be down. */
const QUIET_MS = 5 * 60_000;

/** What waits on a person (offers to recheck or match, collectors that failed), the stores and how
 * they are collected, and every drive to correct: one tab each. The tabs not shown stay as they
 * were left, so nothing typed in one is lost by looking at another. */
export function AdminView({ api, now, nextId, recentDays, storage, listings, tab, tabHref, onTab, queue, queuePage, queueSize, queueError, onQueuePage, onQueueSize, stores, onRecorded, onChanged }: Props) {
  const [runs, setRuns] = useState<CollectorRun[] | null>(null);
  const [runsError, setRunsError] = useState('');
  const [issue, setIssue] = useState<Issue | null>(null);
  const [search, setSearch] = useState('');
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [status, setStatus] = useState<CollectorStatus | null>(null);
  /** What the collector is doing and how its last runs went, asked again every so often: a run
   * starts, gets on and ends while the page is open. */
  const refresh = useCallback(async (active: () => boolean = () => true) => {
    await Promise.all([
      api.latestRuns().then(found => { if (active()) { setRuns(found); setRunsError(''); } })
        .catch(err => { if (active()) setRunsError(err instanceof Error ? err.message : 'Unknown error.'); }),
      // Without it the page still shows how the last runs went.
      api.collectorStatus().then(found => { if (active()) setStatus(found); }).catch(() => {}),
    ]);
  }, [api]);
  useEffect(() => {
    let active = true;
    void refresh(() => active);
    const timer = setInterval(() => { void refresh(() => active); }, REFRESH_MS);
    return () => { active = false; clearInterval(timer); };
  }, [refresh]);
  const checkedAt = now();
  const storeLabel = (key: string) => stores.find(store => store.key === key)?.name ?? key;
  const overdue = overdueForRecheck(listings, checkedAt, recentDays);
  const waiting = overdue.length + queue.total;
  const failed = (runs ?? []).filter(run => !run.completed);
  const groups = groupByDrive(listings, 'unit-asc').map(group => ({ group, found: driveIssues(group, checkedAt, recentDays) }));
  const matching = new Set(queryListings(listings, { ...defaultQuery(), search }, checkedAt, recentDays).map(groupKeyFor));
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
      <RecheckQueue offers={overdue} recentDays={recentDays} api={api} nextId={nextId} onChanged={onChanged} />
      <ReviewQueue items={queue.items} total={queue.total} page={queuePage} pageSize={queueSize} onPage={onQueuePage} onPageSize={onQueueSize}
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
          {failed.length > 0 && <ul className="failed-runs">{failed.map(run => <li key={run.source}>
            <span className="status critical">{storeLabel(run.source)} failed</span>{' · '}<time dateTime={run.finished_at}>{dateLabel(run.finished_at)}</time></li>)}</ul>}
          <a className="seller-link" href={tabHref('stores')} onClick={onTab('stores')}>See every store’s last run</a>
        </>)}
      </section>
    </div>
    <div hidden={tab !== 'stores'}>
      <SourcesSection api={api} sources={stores} listings={listings} runs={runs} status={status} now={now}
        onChanged={async notice => { await Promise.all([onChanged(notice), refresh()]); }} />
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
            {issueLabel(value, recentDays)} ({groups.filter(({ found }) => found.includes(value)).length})</button>)}
        </div>
        <Text size="sm" c="dimmed" mb="xs">{shown.length} of {groups.length} drives{issue && ` · ${issueLabel(issue, recentDays)}`}</Text>
        {groups.length === 0 ? <Text size="sm" c="dimmed">No drives yet.</Text> : <div className="sheet-scroll"><Table aria-label="Drives" verticalSpacing="sm">
          <Table.Thead><Table.Tr><Table.Th>Drive</Table.Th><Table.Th>MPN</Table.Th><Table.Th className="numeric">Capacity</Table.Th>
            <Table.Th className="numeric">Offers</Table.Th><Table.Th>Needs attention</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{pages.shown.map(({ group, found }) => <Table.Tr key={group.key} className="drive-row" onClick={() => setSelectedKey(group.key)}>
            <Table.Td><button type="button" className="drive-link">{group.representative.title}</button></Table.Td>
            <Table.Td className="mono">{group.drive?.mpn ?? group.representative.mpn ?? '—'}</Table.Td>
            <Table.Td className="numeric">{capacityLabel(group.representative.capacity_gb)}</Table.Td>
            <Table.Td className="numeric">{group.listings.length}</Table.Td>
            <Table.Td className="secondary">{found.map(value => issueLabel(value, recentDays)).join(', ') || '—'}</Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table></div>}
        <Pager label="Drives" page={pages.page} total={shown.length} pageSize={drivesPerPage} onPage={pages.setPage} onPageSize={setDrivesPerPage} />
      </section>
    </div>
    {selected.length > 0 && <DriveDetails api={api} now={now} nextId={nextId} listings={listings} driveKey={selectedKey!} key={selectedKey} sort="unit-asc"
      knownCapacities={Object.fromEntries(listings.map(listing => [listing.mpn, listing.capacity_gb]))} manage
      onClose={() => setSelectedKey(null)} onRecorded={onRecorded} onChanged={onChanged} />}
  </>;
}
