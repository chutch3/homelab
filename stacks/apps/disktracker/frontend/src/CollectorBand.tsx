import type { CollectorStatus, Run, Source } from './api';
import { endedBadly } from './admin-overview';
import { ageLabel } from './admin-overview';

const HOUR = 3_600_000;
/** The lane runs from this many hours ago to this many ahead. */
const BACK = 24, AHEAD = 8;

type Props = {
  /** The stores a collector reads, each with when it is next due. */
  sources: Source[];
  /** Every run that finished in the last day. */
  runs: Run[];
  /** What is running now; null until it is known. */
  status: CollectorStatus | null;
  now: Date;
};

/** The last day of collecting as a lane for each store: a mark for each run (a failed one told
 * apart), one for a run in progress, and one for when the store is next due if that is within
 * eight hours. Each lane says the same in words. */
export function CollectorBand({ sources, runs, status, now }: Props) {
  const start = now.getTime() - BACK * HOUR, span = (BACK + AHEAD) * HOUR;
  const along = (moment: number) => `${(Math.max(moment, start) - start) / span * 100}%`;
  const long = (from: number, to: number) => `${(to - Math.max(from, start)) / span * 100}%`;
  return <div className="band">
    {sources.map(source => {
      const own = runs.filter(run => run.source === source.key), failed = own.filter(endedBadly).length;
      const running = status?.running.find(run => run.source === source.key);
      const due = source.next_run_at === null ? null : Date.parse(source.next_run_at);
      const soon = due !== null && due > now.getTime() && due <= now.getTime() + AHEAD * HOUR;
      const said = `${source.name}: ${own.length ? `${own.length} run${own.length === 1 ? '' : 's'}` : 'no runs'} in the last 24 hours`
        + `${failed ? `, ${failed} failed` : ''}${running ? ', running now' : ''}${soon ? `, next due in ${ageLabel(due - now.getTime())}` : ''}.`;
      return <div key={source.key} className="band-lane"><span className="band-name" aria-hidden="true">{source.name}</span>
        <div role="img" aria-label={said} className="band-track">
          {own.map(run => <span key={run.id} className={endedBadly(run) ? 'band-run failed' : 'band-run'}
            style={{ left: along(Date.parse(run.started_at)), width: long(Date.parse(run.started_at), Date.parse(run.finished_at ?? run.updated_at)) }} />)}
          {running && <span className="band-running" style={{ left: along(Date.parse(running.started_at)), width: long(Date.parse(running.started_at), now.getTime()) }} />}
          {soon && <span className="band-due" style={{ left: along(due) }} />}
        </div></div>;
    })}
    <div className="band-axis" aria-hidden="true">{[[-24, '24h ago'], [-16, '16h'], [-8, '8h'], [0, 'Now'], [8, '+8h']].map(([hours, text]) =>
      <span key={text} style={{ left: `${(Number(hours) + BACK) / (BACK + AHEAD) * 100}%` }}>{text}</span>)}</div>
    <ul className="band-key" aria-hidden="true"><li><span className="band-run" />Finished</li><li><span className="band-running" />Running</li>
      <li><span className="band-run failed" />Failed</li><li><span className="band-due" />Due</li></ul>
  </div>;
}
