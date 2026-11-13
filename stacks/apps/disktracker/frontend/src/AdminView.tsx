import { useCallback, useEffect, useState, type MouseEvent } from 'react';
import { Alert, Button, Text } from '@mantine/core';
import type { CollectorStatus, Run, DisktrackerApi, OfferSummary, RecordedPrice, Source } from './api';
import { ageLabel, elapsedLabel, endedBadly } from './admin-overview';
import { CollectorBand } from './CollectorBand';
import { DriveDetails } from './DriveDetails';
import { DrivesSection } from './DrivesSection';
import { defaultQuery } from './listing-query';
import { RecheckQueue } from './RecheckQueue';
import { SourcesSection } from './SourcesSection';
import { ConditionRulesSection } from './ConditionRulesSection';
import { ReviewQueue } from './ReviewQueue';
import { adminTabs, type AdminTab } from './view';

type Props = {
  api: DisktrackerApi; now: () => Date; nextId: () => string; recentDays: number;
  storage: Pick<Storage, 'getItem' | 'setItem'>;
  stores: Source[];
  /** Hand-entered offers overdue for a check, oldest first, as the server lists them. */
  toRecheck: OfferSummary[];
  /** Counts the app's changes: what the page loads itself is loaded again after each. */
  revision: number;
  /** The tab shown, and each tab's address and the way to it. */
  tab: AdminTab; tabHref: (tab: AdminTab) => string; onTab: (tab: AdminTab) => (event: MouseEvent) => void;
  /** Every offer waiting for review, however the queue is narrowed. */
  queueAll: number;
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
export function AdminView({ api, now, nextId, recentDays, storage, toRecheck, revision, tab, tabHref, onTab, queueAll, stores, onRecorded, onChanged }: Props) {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [runsError, setRunsError] = useState('');
  /** The drive open in the panel, by its key, and the title it is named by. */
  const [selected, setSelected] = useState<{ key: string; title: string } | null>(null);
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
      <ReviewQueue api={api} storage={storage} stores={stores} all={queueAll} revision={revision} onChanged={() => onChanged()} />
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
      <SourcesSection api={api} storage={storage} sources={stores} revision={revision} runs={runs} status={status} now={now}
        onChanged={async notice => { await Promise.all([onChanged(notice), refresh()]); }} />
    </div>
    <div hidden={tab !== 'rules'}>
      <ConditionRulesSection api={api} />
    </div>
    <div hidden={tab !== 'drives'}>
      <DrivesSection api={api} storage={storage} recentDays={recentDays} revision={revision} onSelect={(key, title) => setSelected({ key, title })} />
    </div>
    {selected && <DriveDetails api={api} now={now} nextId={nextId} driveKey={selected.key} title={selected.title} revision={revision} key={selected.key} sort="unit-asc"
      manage besideTable={false} recentDays={recentDays} days={defaultQuery().days}
      onClose={() => setSelected(null)} onRecorded={onRecorded} onChanged={onChanged} />}
  </>;
}
