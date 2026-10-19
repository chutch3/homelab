import { expect, it } from 'vitest';
import { ageLabel, elapsedLabel } from '../../src/admin-overview';

it.each([[30 * 60_000, '<1h'], [3_600_000, '1h'], [5 * 3_600_000, '5h'],
  [47 * 3_600_000, '47h'], [48 * 3_600_000, '2d'], [5 * 86_400_000, '5d']])(
  'says an age of %i ms as "%s"', (age, label) => {
    expect(ageLabel(age)).toBe(label);
  },
);

it.each([[20_000, 'under a minute'], [60_000, '1 minute'], [20 * 60_000, '20 minutes'], [59 * 60_000, '59 minutes'],
  [3_600_000, '1h'], [125 * 60_000, '2h'], [47 * 3_600_000, '47h'], [48 * 3_600_000, '2d']])(
  'says %i ms elapsed as "%s", to the minute within the hour', (elapsed, label) => {
    expect(elapsedLabel(elapsed)).toBe(label);
  },
);
