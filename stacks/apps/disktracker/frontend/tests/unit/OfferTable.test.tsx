import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { OfferTable } from '../../src/OfferTable';
import type { Listing } from '../../src/api';
import { checkedAt, historyPrices, makeListing } from '../fixtures/listings';

afterEach(cleanup);

const noActions = { checking: null as string | null, onCheck: () => {}, check: () => null, onEdit: () => {}, onDelete: () => {} };
function renderOffers(listings: Listing[], actions = noActions) {
  render(<MantineProvider env="test"><OfferTable listings={listings} lowestId={null} {...actions} /></MantineProvider>);
  return within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
}

it('shows one row per seller, in the given order, with its total, marking the lowest price', () => {
  const a = makeListing('a', { seller: 'eBay - drivedeals' }, { item_price_cents: 46000, total_cents: 48700 });
  const b = makeListing('b', { seller: 'ServerPartDeals' }, { item_price_cents: 45000, total_cents: 49900 });
  render(<MantineProvider env="test"><OfferTable listings={[a, b]} lowestId="a" {...noActions} /></MantineProvider>);
  const rows = within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
  expect(rows.map(row => within(row).getAllByRole('cell')[0].textContent)).toEqual(['eBay - drivedeals', 'ServerPartDeals']);
  expect(within(rows[0]).getByText('$487.00')).toBeVisible();
  expect(within(rows[1]).getByText('$499.00')).toBeVisible();
  expect(within(rows[0]).getByText('Lowest price')).toBeVisible();
  expect(within(rows[1]).queryByText('Lowest price')).not.toBeInTheDocument();
});

it("shows each seller's change in total since its previous price", () => {
  const tracked = makeListing('h', { observations: historyPrices, latest: historyPrices[1] });
  const fresh = makeListing('f');
  render(<MantineProvider env="test"><OfferTable listings={[tracked, fresh]} lowestId={null} {...noActions} /></MantineProvider>);
  const rows = within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
  expect(within(rows[0]).getByText('▼ $15.00 (6.5%)')).toBeVisible();
  expect(within(rows[1]).queryByText(/[▼▲]/)).not.toBeInTheDocument();
});

it('offers the store page link and Record price inline, and the rarer actions in a menu', async () => {
  const user = userEvent.setup();
  const actions = { ...noActions, onCheck: vi.fn(), onEdit: vi.fn(), onDelete: vi.fn() };
  const listing = makeListing('a', { seller: 'ServerPartDeals', url: 'https://example.com/a' });
  const row = within(renderOffers([listing], actions)[0]);
  expect(row.getByRole('link', { name: 'Open store page ↗' })).toHaveAttribute('href', 'https://example.com/a');
  expect(row.getByRole('button', { name: 'Record price' })).toHaveAttribute('aria-expanded', 'false');
  await user.click(row.getByRole('button', { name: 'Record price' }));
  expect(actions.onCheck).toHaveBeenCalledWith('a');
  await user.click(row.getByRole('button', { name: 'More actions for ServerPartDeals' }));
  await user.click(screen.getByRole('menuitem', { name: 'Edit offer' }));
  expect(actions.onEdit).toHaveBeenCalledWith(listing);
  await user.click(row.getByRole('button', { name: 'More actions for ServerPartDeals' }));
  await user.click(screen.getByRole('menuitem', { name: 'Delete offer' }));
  expect(actions.onDelete).toHaveBeenCalledWith(listing);
});

it("shows the offer's $/TB, check time, and total, leaving its condition to the switch above", () => {
  const unknownTotal = makeListing('u', { condition: 'manufacturer_recertified' },
    { item_price_cents: 36999, shipping_cents: 0, total_cents: 36999, price_per_tb: '20.56' });
  const priced = makeListing('p', { condition: 'new' }, { price_per_tb: '29.44' });
  const [first, second] = renderOffers([unknownTotal, priced]).map(row => within(row));
  expect(first.queryByText('Manufacturer recertified')).not.toBeInTheDocument();
  expect(first.getByText('$369.99')).toBeVisible();
  expect(first.queryByText(/^Item/)).not.toBeInTheDocument();
  expect(second.getByText('$29.44')).toBeVisible();
  expect(second.getByText(checkedAt.toLocaleString())).toHaveAttribute('datetime', checkedAt.toISOString());
});

it('names an Other offer by its store', () => {
  const rows = renderOffers([makeListing('m', { store: 'other', seller: 'Beach Audio' })]);
  expect(within(rows[0]).getAllByRole('cell')[0]).toHaveTextContent('Beach Audio');
  expect(within(rows[0]).getByRole('button', { name: 'More actions for Beach Audio' })).toBeVisible();
});

it('marks sold-out offers, flags shipping not included, and shows when each offer was last checked', () => {
  const soldOut = makeListing('s', { seller: 'Cheap shop' }, { in_stock: false });
  const unknownShipping = makeListing('u', { seller: 'Pricier shop', last_checked_at: '2026-09-22T11:00:00Z' },
    { shipping_cents: null, shipping_known: false, observed_at: '2026-09-20T12:00:00Z' });
  const [first, second] = renderOffers([soldOut, unknownShipping]).map(row => within(row));
  expect(first.getByText('Out of stock')).toBeVisible();
  expect(first.queryByText('Shipping not included')).not.toBeInTheDocument();
  expect(second.getByText('Shipping not included')).toBeVisible();
  expect(second.queryByText('Out of stock')).not.toBeInTheDocument();
  expect(second.getByText(new Date('2026-09-22T11:00:00Z').toLocaleString())).toBeVisible();
});

it('shows the price check under the offer being checked, and puts it away when Record price is chosen again', async () => {
  const user = userEvent.setup();
  const onCheck = vi.fn();
  const listings = [makeListing('a', { seller: 'Shop A' }), makeListing('b', { seller: 'Shop B' })];
  render(<MantineProvider env="test"><OfferTable listings={listings} lowestId={null} {...noActions} checking="b" onCheck={onCheck}
    check={listing => <span>check {listing.id}</span>} /></MantineProvider>);
  const rows = within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('row').slice(1);
  expect(rows.map(row => row.textContent?.includes('check'))).toEqual([false, false, true]);
  expect(rows[2]).toHaveTextContent('check b');
  expect(within(screen.getByRole('table', { name: 'Offers' })).getAllByRole('columnheader').map(header => header.textContent))
    .toEqual(['Store', '$/TB', 'Total', 'Checked', 'Actions']);
  await user.click(within(rows[1]).getByRole('button', { name: 'Record price' }));
  expect(onCheck).toHaveBeenCalledWith(null);
});
