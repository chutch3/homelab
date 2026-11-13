import type { Run } from './api';

/** How a run went, in plain words: completed, with offers that failed when some did; still
 * running; stopped as asked; failed or interrupted, with what went wrong when it is known. */
export type RunOutcome = { label: string; tone: 'good' | 'warning' | 'running' | 'neutral' | 'critical'; reason: string | null };

export function runOutcome({ status, failed, reason }: Run): RunOutcome {
  if (status === 'completed') return failed
    ? { label: `Completed, ${failed} offer${failed === 1 ? '' : 's'} failed`, tone: 'warning', reason: null }
    : { label: 'Completed', tone: 'good', reason: null };
  if (status === 'running') return { label: 'Running', tone: 'running', reason: null };
  if (status === 'stopped') return { label: 'Stopped as asked', tone: 'neutral', reason: null };
  return { label: status === 'abandoned' ? 'Interrupted' : 'Failed', tone: 'critical', reason };
}

const days = ['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays'];
const two = (value: string) => value.padStart(2, '0');

/** A store's cron schedule in plain words, for the schedules stores use; null for any other,
 * which is shown as it is written. Schedules run in UTC. */
export function scheduleLabel(cron: string): string | null {
  const [minute, hour, day, month, weekday, ...more] = cron.trim().split(/\s+/);
  if (more.length || !/^\d+$/.test(minute ?? '') || day !== '*' || month !== '*') return null;
  const every = /^\*(?:\/(\d+))?$/.exec(hour);
  if (every && weekday === '*') {
    const hours = Number(every[1] ?? 1);
    return `${hours === 1 ? 'Every hour' : `Every ${hours} hours`}${minute === '0' ? '' : `, at :${two(minute)}`}`;
  }
  if (!/^\d+(,\d+)*$/.test(hour)) return null;
  const times = hour.split(',').map(at => `${two(at)}:${two(minute)}`).join(' and ');
  if (weekday === '*') return `Daily at ${times} UTC`;
  return /^[0-6]$/.test(weekday) ? `${days[Number(weekday)]} at ${times} UTC` : null;
}
