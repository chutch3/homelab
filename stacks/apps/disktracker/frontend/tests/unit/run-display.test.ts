import { expect, it } from 'vitest';
import { runOutcome, scheduleLabel } from '../../src/run-display';
import type { Run } from '../../src/api';

const run = (fields: Partial<Run>): Run => ({
  id: 'r', source: 'goharddrive', status: 'completed', started_at: '2026-09-22T10:00:00Z', updated_at: '2026-09-22T10:05:00Z',
  finished_at: '2026-09-22T10:05:00Z', reason: null, seen: 10, recorded: 10, queued: 0, ignored: 0, failed: 0, rechecked: 0,
  recheck_failed: 0, stop_requested: false, ...fields,
});

it('says how a run went in plain words, a failure with what went wrong', () => {
  expect(runOutcome(run({}))).toEqual({ label: 'Completed', tone: 'good', reason: null });
  expect(runOutcome(run({ failed: 15 }))).toEqual({ label: 'Completed, 15 offers failed', tone: 'warning', reason: null });
  expect(runOutcome(run({ failed: 1 }))).toEqual({ label: 'Completed, 1 offer failed', tone: 'warning', reason: null });
  expect(runOutcome(run({ status: 'running', finished_at: null }))).toEqual({ label: 'Running', tone: 'running', reason: null });
  expect(runOutcome(run({ status: 'stopped' }))).toEqual({ label: 'Stopped as asked', tone: 'neutral', reason: null });
  expect(runOutcome(run({ status: 'failed', reason: 'HTTP 503' }))).toEqual({ label: 'Failed', tone: 'critical', reason: 'HTTP 503' });
  expect(runOutcome(run({ status: 'abandoned', reason: 'The collector restarted.' })))
    .toEqual({ label: 'Interrupted', tone: 'critical', reason: 'The collector restarted.' });
  // Ended before runs said why.
  expect(runOutcome(run({ status: 'failed' })).reason).toBeNull();
});

it('reads the schedules stores use in plain words, and leaves any other as it is written', () => {
  expect(scheduleLabel('0 */8 * * *')).toBe('Every 8 hours');
  expect(scheduleLabel('0 * * * *')).toBe('Every hour');
  expect(scheduleLabel('30 */6 * * *')).toBe('Every 6 hours, at :30');
  expect(scheduleLabel('0 3 * * *')).toBe('Daily at 03:00 UTC');
  expect(scheduleLabel('15 3,15 * * *')).toBe('Daily at 03:15 and 15:15 UTC');
  expect(scheduleLabel('0 3 * * 1')).toBe('Mondays at 03:00 UTC');
  expect(scheduleLabel('0 3 1 * *')).toBeNull();
  expect(scheduleLabel('*/5 * * * *')).toBeNull();
});
