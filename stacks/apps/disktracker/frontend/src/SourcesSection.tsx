import { useEffect, useState } from 'react';
import { Alert, Button, Group, Switch, Table, Text, VisuallyHidden } from '@mantine/core';
import type { CollectorRun, CollectorStatus, ListingsApi, ListingSummary, Source, SourceBasis, SourceInput, SourceKindDescription } from './api';
import { ageLabel, freshness } from './admin-overview';
import { DeleteSourceDialog } from './DeleteSourceDialog';
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
  return new Date(next_run_at) <= now ? 'Due now' : `Next ${dateLabel(next_run_at)}`;
}
const inputOf = ({ id: _id, next_run_at: _next, ...input }: Source): SourceInput => input;

type Props = {
  api: ListingsApi; now: () => Date;
  /** Every store, loaded once by the app, and the offers recorded under them. */
  sources: Source[]; listings: ListingSummary[];
  /** Each collector's last run; null until they are loaded, or when they could not be. */
  runs: CollectorRun[] | null;
  /** What the collector is doing now; null until it is known. */
  status: CollectorStatus | null;
  /** One changed, so the app reloads them, saying what happened when told. */
  onChanged: (notice?: string) => Promise<void>;
};

/** The stores offers are recorded under: how each is collected (or that it is entered by hand),
 * whether it is running or waiting its turn, how its last run went, how fresh its prices are, and
 * on what permission it is collected. A store waiting is run next with Run now; one running is
 * stopped, once that is confirmed. */
export function SourcesSection({ api, sources, listings, runs, status, now, onChanged }: Props) {
  const [editing, setEditing] = useState<Source | 'new' | null>(null);
  const [deleting, setDeleting] = useState<Source | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  /** The store whose run is being asked about before it is stopped, and those already asked to stop. */
  const [confirming, setConfirming] = useState<string | null>(null);
  const [stopping, setStopping] = useState<string[]>([]);
  const [error, setError] = useState('');
  /** The kinds of store there are, each as its reader describes it: what they are called here, and what the form asks for. */
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
    try { await api.runSource(source.id); setError(''); await onChanged(`${source.name} goes next: the collector takes it once the store it is on is done.`); }
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
  const fresh = freshness(listings, checkedAt, sources);
  return <section aria-labelledby="sources-heading" className="admin-section">
    <Group justify="space-between" align="end" mb="xs">
      <div>
        <h2 id="sources-heading">Stores</h2>
        <Text size="sm" c="dimmed">Every store offers are recorded under: collected on its own schedule, or entered by hand.</Text>
      </div>
      <Button variant="default" onClick={() => setEditing('new')}>Add store</Button>
    </Group>
    {error && <Alert color="red" role="alert" mb="sm">{error}</Alert>}
    {sources.length === 0 ? <Text size="sm">No stores yet.</Text>
      : <div className="sheet-scroll"><Table aria-label="Stores" verticalSpacing="sm">
        <Table.Thead><Table.Tr><Table.Th>Store</Table.Th><Table.Th>Collected</Table.Th>
          <Table.Th>Schedule</Table.Th><Table.Th>Last run</Table.Th><Table.Th>Prices</Table.Th><Table.Th>Permission</Table.Th><Table.Th>Collect</Table.Th>
          <Table.Th><VisuallyHidden>Actions</VisuallyHidden></Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{sources.map(source => {
          // A store entered by hand is never collected: no schedule, run, permission, switch or Run now.
          const kind = kinds.find(known => known.kind === source.kind);
          const collected = kind?.collected ?? source.kind !== 'manual';
          const run = runs?.find(found => found.source === source.key);
          const progress = status?.running.find(found => found.source === source.key);
          const prices = fresh.find(row => row.store.key === source.key);
          return <Table.Tr key={source.id}>
            <Table.Td><strong>{source.name}</strong></Table.Td>
            <Table.Td>{kind?.label ?? source.kind}</Table.Td>
            <Table.Td>{collected ? <><code>{source.schedule}</code><div className="secondary">{nextRunLabel(source, checkedAt, status)}</div></> : '—'}</Table.Td>
            <Table.Td>{progress ? <>
              <span className="status running">● Running</span>
              <div className="secondary">since <time dateTime={progress.started_at}>{dateLabel(progress.started_at)}</time></div>
              <div className="secondary">{progress.seen} seen · {progress.recorded} recorded · {progress.queued} queued · {progress.ignored} ignored · {progress.failed} failed</div>
            </> : !collected || runs === null ? '—' : !run ? 'No run yet' : <>
              {run.completed ? <span className="status good">✓ Completed</span>
                : run.stopped ? <span className="status">■ Stopped</span> : <span className="status critical">✕ Failed</span>}
              <div className="secondary"><time dateTime={run.finished_at}>{dateLabel(run.finished_at)}</time></div>
              <div className="secondary">{run.seen} seen · {run.recorded} recorded · {run.queued} queued · {run.failed} failed · {run.rechecked} rechecked</div>
            </>}</Table.Td>
            <Table.Td>{prices ? <>{prices.offers} offer{prices.offers === 1 ? '' : 's'}
              <div className="secondary" title={`Last checked ${dateLabel(prices.latest)}`}>median age {ageLabel(prices.medianAgeMs)}</div></> : '—'}</Table.Td>
            <Table.Td>{collected ? labelOf(sourceBases, source.basis) : '—'}</Table.Td>
            <Table.Td>{collected && <Switch checked={source.enabled} aria-label={`Collect from ${source.name}`} onChange={() => toggle(source)} />}</Table.Td>
            <Table.Td>{confirming === source.id
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
    {editing && <SourceForm api={api} kinds={kinds} source={editing === 'new' ? null : editing}
      onClose={() => setEditing(null)} onSaved={async () => { setEditing(null); await onChanged(); }}
      onDelete={source => { setEditing(null); setDeleting(source); }} />}
    {deleting && <DeleteSourceDialog source={deleting} api={api} onClose={() => setDeleting(null)} onDeleted={() => onChanged()} />}
  </section>;
}
