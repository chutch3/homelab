import { afterEach, expect, it } from 'vitest';
import { cleanup, render, waitFor } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import type { TrendSeries } from '../../src/api';
import { TrendChart } from '../../src/TrendChart';

afterEach(cleanup);

const series: TrendSeries = { counted: 3, of: 3, points: [
  { days_ago: 90, median: 2000, low: 1500, high: 2500 }, { days_ago: 10, median: 1600, low: 1300, high: 2300 }, { days_ago: 0, median: 1600, low: 1300, high: 2300 },
] };
function show(band: boolean, days = 90) {
  const { container } = render(<MantineProvider env="test"><TrendChart series={series} days={days} domain={[1000, 3000]} band={band} format={value => `$${value / 100}`} /></MantineProvider>);
  return {
    lines: () => [...container.querySelectorAll('.recharts-line-curve')].filter(line => line.getAttribute('d')),
    ticks: (axis: 'xAxis' | 'yAxis') => [...container.querySelectorAll(`.recharts-${axis}-tick-labels text`)].map(tick => tick.textContent),
  };
}

it('draws the median with the middle half either side of it, over the days asked about, on the scale it is given', async () => {
  const { lines, ticks } = show(true);
  await waitFor(() => expect(lines()).toHaveLength(3));
  expect(ticks('xAxis')).toEqual(['90d ago', '60', '30', 'Today']);
  expect(ticks('yAxis')).toEqual(['$10', '$20', '$30']);
});

it('draws the median alone when there is no middle half worth showing', async () => {
  const { lines } = show(false);
  await waitFor(() => expect(lines()).toHaveLength(1));
});

it('names the days along its axis in whole days, whatever the period', async () => {
  const { lines, ticks } = show(false, 14);
  await waitFor(() => expect(lines()).toHaveLength(1));
  expect(ticks('xAxis')).toEqual(['14d ago', '9', '5', 'Today']);
});
