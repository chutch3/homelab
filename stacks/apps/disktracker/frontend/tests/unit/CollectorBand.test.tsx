import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import type { Run } from '../../src/api';
import { CollectorBand } from '../../src/CollectorBand';
import { checkedAt, makeSource } from '../fixtures/listings';

afterEach(cleanup);

const hoursAgo = (hours: number) => new Date(checkedAt.getTime() - hours * 3_600_000).toISOString();
const run = (source: string, started: number, finished: number | null, fields: Partial<Run> = {}): Run => ({
  id: `${source}-${started}`, source, status: finished === null ? 'running' : 'completed', started_at: hoursAgo(started),
  updated_at: hoursAgo(finished ?? 0), finished_at: finished === null ? null : hoursAgo(finished), reason: null,
  seen: 1, recorded: 1, queued: 0, ignored: 0, failed: 0, rechecked: 0, recheck_failed: 0, stop_requested: false, ...fields,
});
const sources = [
  makeSource('serverpartdeals', 'ServerPartDeals', { next_run_at: hoursAgo(-4) }),
  makeSource('goharddrive', 'GoHardDrive', { next_run_at: hoursAgo(-20) }),
  makeSource('westerndigital', 'Western Digital'),
];
const lane = (name: string) => screen.getByRole('img', { name: new RegExp(`^${name}:`) });
const marks = (name: string, kind: string) => [...lane(name).querySelectorAll<HTMLElement>(`.band-${kind}`)];

it('draws each store a lane of its runs over the last day, what is running, and when it is next due within eight hours', () => {
  render(<CollectorBand sources={sources} now={checkedAt}
    runs={[run('serverpartdeals', 20.5, 20), run('serverpartdeals', 12.5, 12), run('goharddrive', 6.5, 6, { status: 'failed' })]}
    status={{ seen_at: hoursAgo(0), waiting: [], running: [run('westerndigital', 0.5, null, { seen: 9, recorded: 9 })] }} />);
  expect(lane('ServerPartDeals')).toHaveAccessibleName('ServerPartDeals: 2 runs in the last 24 hours, next due in 4h.');
  expect(lane('GoHardDrive')).toHaveAccessibleName('GoHardDrive: 1 run in the last 24 hours, 1 failed.');
  expect(lane('Western Digital')).toHaveAccessibleName('Western Digital: no runs in the last 24 hours, running now.');
  // The lane runs from 24 hours ago to 8 hours ahead: a run from 20.5 to 20 hours ago starts 10.9% along and is 1.6% long.
  expect(marks('ServerPartDeals', 'run').map(mark => [mark.style.left, mark.style.width])).toEqual([['10.9375%', '1.5625%'], ['35.9375%', '1.5625%']]);
  expect(marks('ServerPartDeals', 'due').map(mark => mark.style.left)).toEqual(['87.5%']);
  expect(marks('GoHardDrive', 'run').map(mark => mark.className)).toEqual(['band-run failed']);
  // Due in 20 hours is off the end of the lane.
  expect(marks('GoHardDrive', 'due')).toHaveLength(0);
  expect(marks('Western Digital', 'running').map(mark => [mark.style.left, mark.style.width])).toEqual([['73.4375%', '1.5625%']]);
});

it('does not count a run that was stopped as one that failed', () => {
  render(<CollectorBand sources={sources.slice(0, 1)} now={checkedAt} status={null} runs={[run('serverpartdeals', 3, 2.5, { status: 'stopped' })]} />);
  expect(lane('ServerPartDeals')).toHaveAccessibleName('ServerPartDeals: 1 run in the last 24 hours, next due in 4h.');
  expect(marks('ServerPartDeals', 'run').map(mark => mark.className)).toEqual(['band-run']);
});

it('counts a run abandoned by its collector as one that failed', () => {
  render(<CollectorBand sources={sources.slice(0, 1)} now={checkedAt} status={null} runs={[run('serverpartdeals', 3, 2.5, { status: 'abandoned' })]} />);
  expect(lane('ServerPartDeals')).toHaveAccessibleName('ServerPartDeals: 1 run in the last 24 hours, 1 failed, next due in 4h.');
});
