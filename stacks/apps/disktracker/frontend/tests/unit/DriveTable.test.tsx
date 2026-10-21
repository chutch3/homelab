import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { DriveTable } from '../../src/DriveTable';
import { checkedAt, makeDrive, makeOffer, shoppingListings } from '../fixtures/listings';
import { groupsOf } from '../fixtures/responses';

afterEach(cleanup);

it('DriveTable renders one row per listing, sort indicators, price leaders, and selection', async () => {
  const onSort = vi.fn(), onSelect = vi.fn();
  const groups = groupsOf(shoppingListings);
  render(<MantineProvider env="test"><DriveTable groups={groups} sort="total-asc"
    onSort={onSort} onSelect={onSelect} now={checkedAt} recentDays={7}
    leaders={{ total: new Set(['Small drive']), unit: new Set(['Large drive']) }} ranges={{}} rangeDays={90} onRangeDays={() => {}} /></MantineProvider>);
  const heading = screen.getByRole('columnheader', { name: /Total/ });
  expect(heading).toHaveAttribute('aria-sort', 'ascending');
  await userEvent.click(within(heading).getByRole('button'));
  expect(onSort).toHaveBeenCalledWith('total-desc');
  await userEvent.click(screen.getByTitle('Large drive'));
  expect(onSelect).toHaveBeenCalledWith(groups.find(group => group.offer.id === 'Large drive')!.key, 'new');
  expect(screen.getByText('Lowest total')).toBeVisible();
  expect(screen.getByText('Lowest $/TB')).toBeVisible();
  expect(screen.queryByText(/In stock|Unknown/)).not.toBeInTheDocument();
});

it('shows how many sellers share a drive and surfaces the cheapest one', () => {
  const drive = makeDrive('ST18000NM000J');
  const cheaper = makeOffer('Cheaper seller', { drive, store: 'serverpartdeals', seller: '' }, { total_cents: 20000, price_per_tb: '10.00' });
  const pricier = makeOffer('Pricier seller', { drive, seller: 'GoHardDrive' }, { total_cents: 30000, price_per_tb: '15.00' });
  const groups = groupsOf([cheaper, pricier]);
  render(<MantineProvider env="test"><DriveTable groups={groups} sort="unit-asc" onSort={() => {}} onSelect={() => {}}
    now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }} ranges={{}} rangeDays={90} onRangeDays={() => {}} /></MantineProvider>);
  expect(screen.getByTitle('Cheaper seller')).toBeVisible();
  expect(screen.queryByText('Pricier seller')).not.toBeInTheDocument();
  expect(screen.getByText('ServerPartDeals +1 more')).toBeVisible();
});

it('names the other conditions a drive is sold in, each opening the drive on it, apart from the row itself', async () => {
  const drive = makeDrive('ST18000NM000J');
  const refurbished = makeOffer('Exos X18', { drive, condition: 'refurbished' }, { total_cents: 47000, price_per_tb: '26.11' });
  const recertified = makeOffer('recertified', { drive, condition: 'manufacturer_recertified', seller: 'One' }, { total_cents: 48900, price_per_tb: '27.17' });
  const recertifiedToo = makeOffer('recertified-too', { drive, condition: 'manufacturer_recertified', seller: 'Two' }, { total_cents: 49900, price_per_tb: '27.72' });
  const soldOut = makeOffer('new', { drive, condition: 'new' }, { total_cents: 45000, price_per_tb: '25.00', in_stock: false });
  const onSelect = vi.fn();
  // Shown by its cheapest offer in stock, as the server shows it.
  const [group] = groupsOf([refurbished, soldOut, recertifiedToo, recertified]);
  render(<MantineProvider env="test"><DriveTable groups={[group]} sort="unit-asc" onSort={() => {}} onSelect={onSelect}
    now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }} ranges={{}} rangeDays={90} onRangeDays={() => {}} /></MantineProvider>);
  const row = within(screen.getByTitle('Exos X18').closest('tr')!);
  expect(row.getAllByRole('button').slice(1).map(button => button.textContent)).toEqual(['New Out of stock', 'Recertified from $489.00']);
  await userEvent.click(row.getByRole('button', { name: 'Recertified from $489.00' }));
  expect(onSelect).toHaveBeenCalledTimes(1);
  expect(onSelect).toHaveBeenLastCalledWith(group.key, 'manufacturer_recertified');
  await userEvent.click(row.getByTitle('Exos X18'));
  expect(onSelect).toHaveBeenLastCalledWith(group.key, 'refurbished');
});

it("shows each drive's price range for the days asked about, and leaves the cell empty until its range is known", () => {
  const known = makeOffer('Known drive', { drive: makeDrive('ST18000NM000J') });
  const waiting = makeOffer('Waiting drive');
  const groups = groupsOf([known, waiting]);
  const key = groups.find(group => group.offer.id === 'Known drive')!.key;
  render(<MantineProvider env="test"><DriveTable groups={groups} sort="unit-asc" onSort={() => {}} onSelect={() => {}}
    now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }}
    ranges={{ [key]: { today: 18000, low: 17000, high: 19000, average: 18222, days: 90 } }} rangeDays={90} onRangeDays={() => {}} /></MantineProvider>);
  expect(screen.getAllByRole('columnheader').map(header => header.textContent))
    .toEqual(['Drive', 'Capacity', '$/TB ↑', 'Total', 'Item price vs low, last' + '30 days90 days180 days', 'Checked']);
  const row = (name: string) => within(screen.getByTitle(name).closest('tr')!);
  expect(row('Known drive').getByRole('img', { name: 'Today $180.00, 5.9% above the lowest. Over 90 days: lowest $170.00, average $182.22, highest $190.00.' })).toBeVisible();
  expect(row('Known drive').getAllByRole('cell')[4]).toHaveTextContent('+5.9%');
  expect(row('Waiting drive').queryByRole('img')).not.toBeInTheDocument();
  expect(row('Waiting drive').getAllByRole('cell')[4]).toBeEmptyDOMElement();
});

it('offers the days the range looks back over in its column heading, and tells of a change', async () => {
  const onRangeDays = vi.fn();
  render(<MantineProvider env="test"><DriveTable groups={groupsOf(shoppingListings)} sort="unit-asc" onSort={() => {}} onSelect={() => {}}
    now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }} ranges={{}} rangeDays={90} onRangeDays={onRangeDays} /></MantineProvider>);
  const period = screen.getByRole('combobox', { name: 'Days the range looks back over' });
  expect(period).toHaveValue('90');
  expect(within(period).getAllByRole('option').map(option => option.textContent)).toEqual(['30 days', '90 days', '180 days']);
  await userEvent.selectOptions(period, '180');
  expect(onRangeDays).toHaveBeenCalledExactlyOnceWith(180);
});

it('keeps a long listing title to one line of its row, with the whole of it there on pointing', () => {
  const title = 'Western Digital Ultrastar DC HC530 WUH721414ALE601 14TB 7200RPM 512MB Cache SATA 6.0Gb/s 3.5inch Enterprise Hard Drive (Certified Refurbished) - 3 Year Warranty';
  const groups = groupsOf([makeOffer(title)]);
  render(<MantineProvider env="test"><DriveTable groups={groups} sort="unit-asc" onSort={() => {}} onSelect={() => {}}
    now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }} ranges={{}} rangeDays={90} onRangeDays={() => {}} /></MantineProvider>);
  // The row names the drive; the store's whole title is there on pointing.
  expect(screen.getByTitle(title)).toHaveAccessibleName('18 TB drive MPN-' + title);
});

it('leads each row with the price the list is ordered by: the total when it is, the price per terabyte otherwise', () => {
  const offer = makeOffer('Exos', {}, { total_cents: 19250, price_per_tb: '10.69' });
  const table = (sort: 'unit-asc' | 'total-asc' | 'checked-desc') => {
    cleanup();
    render(<MantineProvider env="test"><DriveTable groups={groupsOf([offer])} sort={sort} onSort={() => {}} onSelect={() => {}}
      now={checkedAt} recentDays={7} leaders={{ total: new Set(), unit: new Set() }} ranges={{}} rangeDays={90} onRangeDays={() => {}} /></MantineProvider>);
    const lead = (text: string) => screen.getByText(text).classList.contains('lead-price');
    return [lead('$10.69'), lead('$192.50')];
  };
  expect(table('unit-asc')).toEqual([true, false]);
  expect(table('total-asc')).toEqual([false, true]);
  expect(table('checked-desc')).toEqual([true, false]);
});
