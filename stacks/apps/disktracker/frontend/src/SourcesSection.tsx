import { useEffect, useState } from 'react';
import { Alert, Button, Group, Switch, Table, Text, VisuallyHidden } from '@mantine/core';
import type { CollectorStatus, Run, DisktrackerApi, Source, SourceBasis, SourceInput, SourceKindDescription, StoreFreshness } from './api';
import { ageLabel, elapsedLabel } from './admin-overview';
import { DeleteSourceDialog } from './DeleteSourceDialog';
import { Pager } from './Pager';
import { usePages, usePageSize } from './paging';
import { runOutcome, scheduleLabel } from './run-display';
import { SourceForm } from './SourceForm';

export const sourceBases: { value: SourceBasis; label: string }[] = [
  { value: 'permission', label: 'Permission granted' },
  { value: 'terms_allow', label: 'Terms allow' },
  { value: 'open_api', label: 'Open API' },
  { value: 'unconfirmed', label: 'Unconfirmed' },
];
const labelOf = <T extends string>(options: { value: T; label: string }[], value: T) =>
  options.find(option => option.value === value)?.label ?? value;
const dateLabel = (value: string) => new Date(value).toLocaleString();
const ordinal = (place: number) => `${place}${place % 100 >= 11 && place % 100 <= 13 ? 'th' : ['th', 'st', 'nd', 'rd'][place % 10] ?? 'th'}`;
/** Where a collected store stands: running, waiting its turn behind those ahead of it, due
 * already, due at a time to come, or not while it is switched off. */
function nextRunLabel({ key, next_run_at, enabled }: Source, now: Date, status: CollectorStatus | null): string {
  if (status?.running.some(run => run.source === key)) return 'Running now';
  const place = status?.waiting.indexOf(key) ?? -1;
  if (place === 0) return 'Next to run';
  if (place > 0) return `Waiting, ${ordinal(place + 1)} in line`;
  if (next_run_at === null) return enabled ? 'Not scheduled' : 'Switched off';
  return new Date(next_run_at) <= now ? 'Due now' : `Next in ${ageLabel(Date.parse(next_run_at) - now.getTime())}`;
}
/** What a run did, in the two counts that say whether it worked, and its failures when it had any. */
const countsLabel = ({ recorded, queued, failed }: { recorded: number; queued: number; failed: number }) =>
  `${recorded} recorded · ${queued} queued${failed ? ` · ${failed} failed` : ''}`;
/** A store as it is entered, from the store as the API gives it back: each field the input takes,
 * and nothing the API gives of its own (its id, key or next run). */
const inputOf = ({ name, kind, base_url, settings, schedule, enabled, transport, basis, obey_robots, notes }: Source): SourceInput =>
  ({ name, kind, base_url, settings, schedule, enabled, transport, basis, obey_robots, notes }) as SourceInput;

type Props = {
  api: DisktrackerApi; now: () => Date;
  /** Keeps how many stores a page shows between visits. */
  storage: Pick<Storage, 'getItem' | 'setItem'>;
  /** Every store, loaded once by the app. */
  sources: Source[];
  /** Counts changes made anywhere: how fresh the stores' prices are is asked again after each. */
  revision: number;
  /** Each collector's last run; null until they are loaded, or when they could not be. */
  runs: Run[] | null;
  /** What the collector is doing now; null until it is known. */
  status: CollectorStatus | null;
  /** One changed, so the app reloads them, saying what happened when told. */
  onChanged: (notice?: string) => Promise<void>;
};

/** The stores offers are recorded under: how each is collected (or that it is entered by hand),
 * whether it is running or waiting its turn, how its last run went, how fresh its prices are, and
 * on what permission it is collected. A store waiting is run next with Run now; one running is
 * stopped, once that is confirmed. Every cell is two lines at most and starts at the top of its
 * row, so a row reads straight across; more stores than fit a page are paged through. */
const signs = { good: '✓', warning: '✓', running: '●', neutral: '■', critical: '✕' } as const;
/** How a store's last run went, in words and a sign. */
function runLabel(run: Run) {
  const { label, tone } = runOutcome(run);
  return <span className={`status ${tone}`}>{signs[tone]} {label}</span>;
}

export function SourcesSection({ api, sources, revision, runs, status, now, storage, onChanged }: Props) {
  const [perPage, setPerPage] = usePageSize(storage, 'stores');
  /** How fresh each store's prices are, as the server reports it; none until it has. */
  const [fresh, setFresh] = useState<StoreFreshness[]>([]);
  useEffect(() => {
    let active = true;
    // Without it the stores are still shown, with no age for their prices.
    api.storeFreshness().then(found => { if (active) setFresh(found); }).catch(() => {});
    return () => { active = false; };
  }, [api, revision]);
  const pages = usePages(sources, perPage);
  const [editing, setEditing] = useState<Source | 'new' | null>(null);
  const [deleting, setDeleting] = useState<Source | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  /** The store whose run is being asked about before it is stopped, and those already asked to stop. */
  const [confirming, setConfirming] = useState<string | null>(null);
  const [stopping, setStopping] = useState<string[]>([]);
  const [error, setError] = useState('');
  /** The kinds of store there are, as the backend describes them: what they are called here, and what the form asks for. */
  const [kinds, setKinds] = useState<SourceKindDescription[]>([]);
  useEffect(() => {
    let active = true;
    api.listSourceKinds().then(found => { if (active) setKinds(found); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'The kinds of store could not be loaded.'); });
    return () => { active = false; };
  }, [api]);
  const toggle = async (source: Source) => {
    try { await api.updateSource(source.id, { ...inputOf(source), enabled: !source.enabled }); setError(''); await onChanged(); }
    catch (err) { setError(err instanceof Error ? err.message : 'The store could not be changed.'); }
  };
  const runNow = async (source: Source) => {
    setRunning(source.id);
    try { await api.runSource(source.id); setError(''); await onChanged(`${source.name} is queued to run next.`); }
    catch (err) { setError(err instanceof Error ? err.message : 'The store could not be asked to run.'); }
    finally { setRunning(null); }
  };
  const stop = async (source: Source) => {
    setConfirming(null);
    try {
      await api.stopSource(source.id); setError(''); setStopping(asked => [...asked, source.id]);
      await onChanged(`${source.name} was asked to stop: it ends once the offer it is reading is done.`);
    } catch (err) { setError(err instanceof Error ? err.message : 'The store could not be asked to stop.'); }
  };
  const checkedAt = now();
  return <section aria-labelledby="sources-heading" className="admin-section">
    <Group justify="space-between" align="end" mb="xs">
      <div>
        <h2 id="sources-heading">Stores</h2>
        <Text size="sm" c="dimmed">Collected on a schedule, or entered by hand.</Text>
      </div>
      <Button variant="default" onClick={() => setEditing('new')}>Add store</Button>
    </Group>
    {error && <Alert color="red" role="alert" mb="sm">{error}</Alert>}
    {sources.length === 0 ? <Text size="sm">No stores yet.</Text>
      : <div className="sheet-scroll"><Table aria-label="Stores" verticalSpacing="sm" className="stores">
        <Table.Thead><Table.Tr><Table.Th>Store</Table.Th>
          <Table.Th>Collect</Table.Th><Table.Th>Schedule</Table.Th><Table.Th>Last run</Table.Th><Table.Th>Prices</Table.Th><Table.Th>Permission</Table.Th>
          <Table.Th><VisuallyHidden>Actions</VisuallyHidden></Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{pages.shown.map(source => {
          // A store entered by hand is never collected: no schedule, run, permission, switch or Run now.
          const kind = kinds.find(known => known.kind === source.kind);
          const collected = kind?.collected ?? source.kind !== 'manual';
          const run = runs?.find(found => found.source === source.key);
          const progress = status?.running.find(found => found.source === source.key);
          const prices = fresh.find(row => row.store === source.key);
          // Whether it is collected, when, and how it last went sit together, after its name.
          return <Table.Tr key={source.id} id={`store-${source.key}`}>
            {/* How it is collected sits under its name: one column fewer to read across. */}
            <Table.Td><strong>{source.name}</strong><div className="secondary">{kind?.label ?? source.kind}</div></Table.Td>
            <Table.Td data-label="Collect">{collected && <Switch checked={source.enabled} aria-label={`Collect from ${source.name}`} onChange={() => toggle(source)} />}</Table.Td>
            <Table.Td data-label="Schedule">{collected ? <>{scheduleLabel(source.schedule) ? <span title={source.schedule}>{scheduleLabel(source.schedule)}</span> : <code>{source.schedule}</code>}
              <div className="secondary">{nextRunLabel(source, checkedAt, status)}</div></> : '—'}</Table.Td>
            <Table.Td data-label="Last run">{progress ? <>
              <span className="status running">● Running</span>
              <time className="secondary" dateTime={progress.started_at} title={dateLabel(progress.started_at)}>for {elapsedLabel(checkedAt.getTime() - Date.parse(progress.started_at))}</time>
              <div className="secondary" title={`${progress.seen} seen · ${progress.recorded} recorded · ${progress.queued} queued · ${progress.ignored} ignored · ${progress.failed} failed`}>{countsLabel(progress)}</div>
            </> : !collected || runs === null ? '—' : !run ? 'No run yet' : <>
              {runLabel(run)}
              <time className="secondary" dateTime={run.finished_at ?? run.updated_at} title={dateLabel(run.finished_at ?? run.updated_at)}>{ageLabel(checkedAt.getTime() - Date.parse(run.finished_at ?? run.updated_at))} ago</time>
              <div className="secondary" title={`${run.seen} seen · ${run.recorded} recorded · ${run.queued} queued · ${run.failed} failed · ${run.rechecked} rechecked`}>{countsLabel(run)}</div>
              {run.reason && <div className="run-reason">{run.reason}</div>}
            </>}</Table.Td>
            <Table.Td data-label="Prices">{prices ? <>{prices.offers} offer{prices.offers === 1 ? '' : 's'}
              <div className="secondary" title={`Last checked ${dateLabel(prices.latest_checked_at)}`}>median age {ageLabel(checkedAt.getTime() - Date.parse(prices.median_checked_at))}</div></> : '—'}</Table.Td>
            <Table.Td data-label="Permission">{collected ? <>{labelOf(sourceBases, source.basis)}
              {!source.obey_robots && <div className="secondary">Ignores robots.txt</div>}</> : '—'}</Table.Td>
            <Table.Td className="store-actions">{confirming === source.id
              ? <Group gap="sm" wrap="nowrap" justify="end"><Text size="sm">Stop this run? What it has recorded is kept.</Text>
                <Button color="red" onClick={() => stop(source)}>Yes, stop</Button>
                <Button variant="default" onClick={() => setConfirming(null)}>Keep running</Button></Group>
              : <Group gap="sm" wrap="nowrap" justify="end">
                {progress ? (stopping.includes(source.id)
                  ? <Button variant="default" aria-label={`Stopping ${source.name}`} disabled>Stopping…</Button>
                  : <Button variant="default" aria-label={`Stop ${source.name}`} onClick={() => setConfirming(source.id)}>Stop</Button>)
                : collected && <Button variant="default" aria-label={`Run ${source.name} now`} loading={running === source.id}
                  disabled={running !== null} onClick={() => runNow(source)}>Run now</Button>}
                <Button variant="default" aria-label={`Edit ${source.name}`} onClick={() => setEditing(source)}>Edit</Button>
              </Group>}</Table.Td>
          </Table.Tr>;
        })}</Table.Tbody>
      </Table></div>}
    <Pager label="Stores" page={pages.page} total={sources.length} pageSize={perPage} onPage={pages.setPage} onPageSize={setPerPage} />
    {editing && <SourceForm api={api} kinds={kinds} source={editing === 'new' ? null : editing}
      onClose={() => setEditing(null)} onSaved={async () => { setEditing(null); await onChanged(); }}
      onDelete={source => { setEditing(null); setDeleting(source); }} />}
    {deleting && <DeleteSourceDialog source={deleting} api={api} onClose={() => setDeleting(null)} onDeleted={() => onChanged()} />}
  </section>;
}
