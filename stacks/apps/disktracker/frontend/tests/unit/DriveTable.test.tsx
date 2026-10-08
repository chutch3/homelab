import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { DriveTable } from '../../src/DriveTable';
import { groupByDrive } from '../../src/drive-groups';
import { checkedAt, makeDrive, makeListing, shoppingListings } from '../fixtures/listings';

afterEach(cleanup);

it('DriveTable renders one row per listing, sort indicators, price leaders, and selection', async () => {
  const onSort = vi.fn(), onSelect = vi.fn();
  const groups = groupByDrive(shoppingListings, 'total-asc');
  render(<MantineProvider env="test"><DriveTable groups={groups} sort="total-asc"
    onSort={onSort} onSelect={onSelect} now={checkedAt} recentDays={7}
    leaders={{ total: new Set(['Small drive']), unit: new Set(['Large drive']) }} /></MantineProvider>);
  const heading = screen.getByRole('columnheader', { name: /Total/ });
  expect(heading).toHaveAttribute('aria-sort', 'ascending');
  await userEvent.click(within(heading).getByRole('button'));
  expect(onSort).toHaveBeenCalledWith('total-desc');
  await userEvent.click(screen.getByRole('button', { name: 'Large drive' }));
  expect(onSelect).toHaveBeenCalledWith(groups.find(group => group.representative.id === 'Large drive')!.key, 'new');
  expect(screen.getByText('Lowest total')).toBeVisible();
  expect(screen.getByText('Lowest $/TB')).toBeVisible();
  expect(screen.queryByText(/In stock|Unknown/)).not.toBeInTheDocument();
});

it('shows how many sellers share a drive and surfaces the cheapest one', () => {
  const drive = makeDrive('ST18000NM000J');
  const cheaper = makeListing('Cheaper seller', { drive, store: 'serverpartdeals', seller: '' }, { total_cents: 20000, price_per_tb: '10.00' });
  const pricier = makeListing('Pricier seller', { drive, seller: 'GoHardDrive' }, { total_cents: 30000, price_per_tb: '15.00' });
  const groups = groupByDrive([pricier, cheaper], 'unit-asc');
  render(<MantineProvider env="test"><DriveTable groups={groups} sort="unit-asc" onSort={() => {}} onSelect={() => {}}
    now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }} /></MantineProvider>);
  expect(screen.getByRole('button', { name: 'Cheaper seller' })).toBeVisible();
  expect(screen.queryByText('Pricier seller')).not.toBeInTheDocument();
  expect(screen.getByText('2 stores')).toBeVisible();
  expect(screen.getByText(/from ServerPartDeals/)).toBeVisible();
});

it('names the other conditions a drive is sold in, each opening the drive on it, apart from the row itself', async () => {
  const drive = makeDrive('ST18000NM000J');
  const refurbished = makeListing('Exos X18', { drive, condition: 'refurbished' }, { total_cents: 47000, price_per_tb: '26.11' });
  const recertified = makeListing('recertified', { drive, condition: 'manufacturer_recertified', seller: 'One' }, { total_cents: 48900, price_per_tb: '27.17' });
  const recertifiedToo = makeListing('recertified-too', { drive, condition: 'manufacturer_recertified', seller: 'Two' }, { total_cents: 49900, price_per_tb: '27.72' });
  const soldOut = makeListing('new', { drive, condition: 'new' }, { total_cents: 45000, price_per_tb: '25.00', in_stock: false });
  const onSelect = vi.fn();
  const [group] = groupByDrive([soldOut, recertifiedToo, recertified, refurbished], 'unit-asc');
  render(<MantineProvider env="test"><DriveTable groups={[group]} sort="unit-asc" onSort={() => {}} onSelect={onSelect}
    now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }} /></MantineProvider>);
  const row = within(screen.getByRole('button', { name: 'Exos X18' }).closest('tr')!);
  expect(row.getAllByRole('button').slice(1).map(button => button.textContent)).toEqual(['New Out of stock', 'Manufacturer recertified from $489.00']);
  await userEvent.click(row.getByRole('button', { name: 'Manufacturer recertified from $489.00' }));
  expect(onSelect).toHaveBeenCalledTimes(1);
  expect(onSelect).toHaveBeenLastCalledWith(group.key, 'manufacturer_recertified');
  await userEvent.click(row.getByRole('button', { name: 'Exos X18' }));
  expect(onSelect).toHaveBeenLastCalledWith(group.key, 'refurbished');
});
