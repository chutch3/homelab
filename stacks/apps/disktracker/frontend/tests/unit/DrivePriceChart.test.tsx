import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { DrivePriceChart } from '../../src/DrivePriceChart';
import { makeDrive, makeListing } from '../fixtures/listings';

afterEach(cleanup);

it('plots each store\'s total for the day, colored differently, with a legend naming each store', () => {
  const drive = makeDrive('ST18000NM003D');
  const a = makeListing('a', { drive, seller: 'ServerPartDeals' }, { total_cents: 49900, item_price_cents: 45000 });
  const b = makeListing('b', { drive, seller: 'eBay - drivedeals' }, { total_cents: 48700, item_price_cents: 46000 });
  const { container } = render(<MantineProvider env="test"><DrivePriceChart listings={[a, b]} /></MantineProvider>);
  const trend = within(screen.getByRole('region', { name: 'Price trend' }));
  const points = container.querySelectorAll('[data-testid="price-chart-point"]');
  expect(points).toHaveLength(2);
  expect(new Set([...points].map(point => point.getAttribute('fill'))).size).toBe(2);
  expect(trend.getByText('ServerPartDeals')).toBeVisible();
  expect(trend.getByText('eBay - drivedeals')).toBeVisible();
  // One day each, so dots and no lines; the price axis frames the prices instead of starting at zero.
  expect([...container.querySelectorAll('.recharts-line-curve')].filter(line => /L/.test(line.getAttribute('d') ?? ''))).toHaveLength(0);
  const prices = [...container.querySelectorAll('.recharts-yAxis-tick-labels text')].map(tick => tick.textContent);
  expect(prices[0]).toBe('$470.00');
  expect(prices[prices.length - 1]).toBe('$510.00');
  expect(trend.queryByLabelText('Price measure')).not.toBeInTheDocument();
});

it('still shows the chart, with a no-data message, when there is nothing to plot', () => {
  const drive = makeDrive('ST18000NM003D');
  const unpriced = makeListing('a', { drive, seller: 'ServerPartDeals', observations: [] });
  const { container } = render(<MantineProvider env="test"><DrivePriceChart listings={[unpriced]} /></MantineProvider>);
  const trend = within(screen.getByRole('region', { name: 'Price trend' }));
  expect(trend.getByText('No price history yet')).toBeVisible();
  expect(container.querySelector('.recharts-surface')).toBeInTheDocument();
  expect(container.querySelectorAll('[data-testid="price-chart-point"]')).toHaveLength(0);
});

it('names the lowest in-stock price, and says nothing of a low when no price was ever in stock', () => {
  const drive = makeDrive('ST18000NM003D');
  const inStock = makeListing('a', { drive, store: 'serverpartdeals', seller: '' }, { total_cents: 49900 });
  const { unmount } = render(<MantineProvider env="test"><DrivePriceChart listings={[inStock]} /></MantineProvider>);
  expect(within(screen.getByRole('region', { name: 'Price trend' })).getByText(/^Lowest price \$499\.00 · ServerPartDeals · \d/)).toBeVisible();
  unmount();
  const soldOut = makeListing('b', { drive }, { in_stock: false });
  render(<MantineProvider env="test"><DrivePriceChart listings={[soldOut]} /></MantineProvider>);
  expect(within(screen.getByRole('region', { name: 'Price trend' })).queryByText(/Lowest price/)).not.toBeInTheDocument();
});
