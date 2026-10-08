import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { DriveObservationTable } from '../../src/DriveObservationTable';
import { makeDrive, makeListing } from '../fixtures/listings';

afterEach(cleanup);

it('lists every price across stores in one table, each under its store, and routes delete clicks to the owning listing', async () => {
  const user = userEvent.setup();
  const drive = makeDrive('ST18000NM003D');
  const a = makeListing('a', { drive, store: 'serverpartdeals', seller: '', condition: 'refurbished' }, { observed_at: '2026-09-20T12:00:00Z', entered_at: '2026-09-20T12:00:00Z' });
  const b = makeListing('b', { drive, store: 'other', seller: 'drivedeals', condition: 'used' }, { observed_at: '2026-09-21T12:00:00Z', entered_at: '2026-09-21T12:00:00Z' });
  const onDelete = vi.fn();
  render(<MantineProvider env="test"><DriveObservationTable listings={[a, b]} onDelete={onDelete} /></MantineProvider>);
  const table = screen.getByRole('table', { name: 'Price history' });
  const rows = within(table).getAllByRole('row').slice(1);
  expect(rows).toHaveLength(2);
  expect(within(rows[0]).getAllByRole('cell')[0]).toHaveTextContent(/^ServerPartDeals$/);
  expect(within(rows[1]).getAllByRole('cell')[0]).toHaveTextContent(/^drivedeals$/);
  expect(within(rows[1]).queryByRole('button', { name: 'Correct observation' })).not.toBeInTheDocument();
  await user.click(within(rows[1]).getByRole('button', { name: 'Delete price' }));
  expect(onDelete).toHaveBeenCalledWith(b, b.latest);
});

it('shows each price with its shipping & fees and total', () => {
  const offer = makeListing('a', {}, { item_price_cents: 18000, shipping_cents: 1250, total_cents: 19250 });
  render(<MantineProvider env="test"><DriveObservationTable listings={[offer]} onDelete={vi.fn()} /></MantineProvider>);
  const table = within(screen.getByRole('table', { name: 'Price history' }));
  expect(table.getAllByRole('columnheader').map(header => header.textContent))
    .toEqual(['Store', 'Checked', 'Item', 'Shipping & fees', 'Total', 'Notes', 'Actions']);
  expect(table.getByText('$12.50')).toBeVisible();
  expect(table.getByText('$192.50')).toBeVisible();
});

it('says shipping was not included when it was unknown', () => {
  const offer = makeListing('a', {}, { item_price_cents: 18000, shipping_cents: null, shipping_known: false, total_cents: 18000 });
  render(<MantineProvider env="test"><DriveObservationTable listings={[offer]} onDelete={vi.fn()} /></MantineProvider>);
  const [row] = within(screen.getByRole('table', { name: 'Price history' })).getAllByRole('row').slice(1);
  expect(within(row).getAllByRole('cell')[3]).toHaveTextContent('Not included');
});
