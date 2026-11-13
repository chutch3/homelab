import { useState } from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { ListingFilters } from '../../src/ListingFilters';
import { knownStores } from '../fixtures/listings';
import { defaultQuery, type ListingQuery } from '../../src/listing-query';

afterEach(() => { cleanup(); vi.useRealTimers(); });

it('ListingFilters emits selections, shows active filters, and clears every constraint', async () => {
  let changed = defaultQuery();
  function Harness() {
    const [query, setQuery] = useState<ListingQuery>(defaultQuery);
    return <ListingFilters query={query} recentDays={7} stores={knownStores} capacities={[{ capacity_gb: 960, drives: 1 }, { capacity_gb: 18000, drives: 3 }]} brands={[{ brand: 'Seagate', drives: 2 }]} conditions={[{ condition: 'new', drives: 3 }, { condition: 'used', drives: 1 }]}
      onChange={next => { changed = next; setQuery(next); }} />;
  }
  render(<MantineProvider env="test"><Harness /></MantineProvider>);
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Search drives'), 'Exos');
  await user.click(screen.getByRole('textbox', { name: 'Capacity' }));
  await user.click(screen.getByRole('option', { name: '18 TB (3)' }));
  const conditions = within(screen.getByRole('group', { name: 'Condition' }));
  // Refurbished is not sold, so it is not offered; a condition asked for stays, to be let go of.
  expect(conditions.getAllByRole('button').map(button => button.textContent)).toEqual(['New (3)', 'Used (1)']);
  await user.click(conditions.getByRole('button', { name: 'New (3)' }));
  await user.click(conditions.getByRole('button', { name: 'Used (1)' }));
  expect(conditions.getByRole('button', { name: 'Used (1)' })).toHaveAttribute('aria-pressed', 'true');
  await user.click(screen.getByRole('button', { name: 'More filters' }));
  await user.click(screen.getByRole('textbox', { name: 'Store' }));
  await user.click(screen.getByRole('option', { name: 'GoHardDrive' }));
  expect(screen.queryByLabelText('Availability')).not.toBeInTheDocument();
  await user.click(screen.getByLabelText('Checked in the last 7 days'));
  await user.click(screen.getByLabelText('In stock only'));
  expect(changed).toMatchObject({ search: 'Exos', capacities: ['18000'], conditions: ['new', 'used'], stores: ['goharddrive'], recentOnly: true, inStockOnly: false });
  expect(screen.getByLabelText('Active filters')).toHaveTextContent('GoHardDrive');
  expect(screen.getByLabelText('Active filters')).toHaveTextContent('18 TB');
  expect(screen.getByLabelText('Active filters')).toHaveTextContent('Including out of stock');
  expect(screen.getByLabelText('Active filters')).not.toHaveTextContent('Used');
  await user.click(conditions.getByRole('button', { name: 'Used (1)' }));
  expect(changed.conditions).toEqual(['new']);
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));
  expect(changed).toEqual(defaultQuery());
  expect(screen.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument();
});

it('applies a typed maximum total once typing has paused, so a half-typed amount never filters', () => {
  vi.useFakeTimers();
  const onChange = vi.fn();
  render(<MantineProvider env="test"><ListingFilters query={defaultQuery()} recentDays={7} stores={knownStores} capacities={[]} brands={[]} conditions={[]} onChange={onChange} /></MantineProvider>);
  const total = screen.getByLabelText('Maximum total (USD)');
  fireEvent.change(total, { target: { value: '1' } });
  act(() => { vi.advanceTimersByTime(300); });
  fireEvent.change(total, { target: { value: '180' } });
  act(() => { vi.advanceTimersByTime(300); });
  expect(onChange).not.toHaveBeenCalled();
  act(() => { vi.advanceTimersByTime(100); });
  expect(onChange).toHaveBeenCalledTimes(1);
  expect(onChange).toHaveBeenCalledWith({ ...defaultQuery(), maxTotal: '180' });
});

it('keeps the order drives are sorted in when the filters are cleared', async () => {
  const onChange = vi.fn();
  render(<MantineProvider env="test"><ListingFilters query={{ ...defaultQuery(), search: 'Exos', sort: 'total-desc' }} recentDays={7} stores={knownStores} capacities={[]} brands={[]} conditions={[]} onChange={onChange} /></MantineProvider>);
  await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
  expect(onChange).toHaveBeenCalledWith({ ...defaultQuery(), sort: 'total-desc' });
});


it('filters by plain specification values, with no SMR management filter', async () => {
  let changed = defaultQuery();
  function Harness() {
    const [query, setQuery] = useState(defaultQuery);
    return <ListingFilters query={query} recentDays={7} stores={knownStores} capacities={[{ capacity_gb: 960, drives: 1 }, { capacity_gb: 18000, drives: 3 }]} brands={[{ brand: 'Seagate', drives: 2 }]} conditions={[{ condition: 'new', drives: 3 }, { condition: 'used', drives: 1 }]}
      onChange={next => { changed = next; setQuery(next); }} />;
  }
  render(<MantineProvider env="test"><Harness /></MantineProvider>);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'More filters' }));
  await user.selectOptions(screen.getByLabelText('Recording type'), 'smr');
  expect(screen.queryByLabelText('SMR management')).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Intended use'), 'nas');
  expect(changed).toMatchObject({ recording_type: 'smr', intended_use: 'nas' });
  expect(screen.queryByText(/verified/i)).not.toBeInTheDocument();
});

it('keeps the interface in view beside the media type, apart from the filters counted on More filters', async () => {
  const onChange = vi.fn();
  const { rerender } = render(<MantineProvider env="test"><ListingFilters query={defaultQuery()} recentDays={7} stores={knownStores} capacities={[]} brands={[]} conditions={[]} onChange={onChange} /></MantineProvider>);
  expect(screen.getByRole('button', { name: 'More filters' })).toHaveAttribute('aria-expanded', 'false');
  const labels = () => screen.getAllByRole('combobox').map(field => (field as HTMLSelectElement).labels?.[0]?.textContent);
  expect(labels()).toEqual(['Media type', 'Interface']);
  await userEvent.selectOptions(screen.getByLabelText('Interface'), 'sas');
  expect(onChange).toHaveBeenCalledExactlyOnceWith({ ...defaultQuery(), interface: 'sas' });
  rerender(<MantineProvider env="test"><ListingFilters query={{ ...defaultQuery(), interface: 'sas' }} recentDays={7} stores={knownStores} capacities={[]} brands={[]} conditions={[]} onChange={onChange} /></MantineProvider>);
  expect(screen.getByLabelText('Active filters')).toHaveTextContent('Interface: SAS');
  expect(screen.getByRole('button', { name: 'More filters' })).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'More filters' }));
  expect(labels()).toEqual(['Media type', 'Interface', 'Form factor', 'Recording type', 'Intended use']);
});

it('keeps In stock only in view beside the conditions, on unless turned off, without opening More filters', async () => {
  const onChange = vi.fn();
  render(<MantineProvider env="test"><ListingFilters query={defaultQuery()} recentDays={7} stores={knownStores} capacities={[]} brands={[]} conditions={[]} onChange={onChange} /></MantineProvider>);
  expect(screen.getByRole('button', { name: 'More filters' })).toHaveAttribute('aria-expanded', 'false');
  const inStock = within(screen.getByRole('group', { name: 'Condition' })).getByRole('checkbox', { name: 'In stock only' });
  expect(inStock).toBeChecked();
  await userEvent.click(inStock);
  expect(onChange).toHaveBeenCalledExactlyOnceWith({ ...defaultQuery(), inStockOnly: false });
});

it('on a phone, keeps the search in view and gathers every other filter behind one button that counts those in force', async () => {
  const matchMedia = (query: string) => ({ matches: query === '(max-width: 700px)', media: query, addEventListener: () => {}, removeEventListener: () => {} });
  Object.defineProperty(window, 'matchMedia', { configurable: true, value: matchMedia });
  try {
    function Harness() {
      const [query, setQuery] = useState<ListingQuery>({ ...defaultQuery(), conditions: ['new'], capacities: ['18000'], media_type: 'hdd' });
      return <ListingFilters query={query} recentDays={7} stores={knownStores} capacities={[{ capacity_gb: 18000, drives: 3 }]} brands={[]}
        conditions={[{ condition: 'new', drives: 3 }, { condition: 'used', drives: 1 }]} onChange={setQuery} />;
    }
    render(<MantineProvider env="test"><Harness /></MantineProvider>);
    const user = userEvent.setup();
    expect(screen.getByLabelText('Search drives')).toBeVisible();
    expect(screen.queryByRole('group', { name: 'Condition' })).not.toBeInTheDocument();
    // A condition, a capacity and a media type.
    const open = screen.getByRole('button', { name: 'Filters (3)' });
    expect(open).toHaveAttribute('aria-expanded', 'false');
    await user.click(open);
    const sheet = within(screen.getByRole('dialog', { name: 'Filters' }));
    // Every filter is in the sheet, those once under More filters too.
    expect(sheet.getByRole('textbox', { name: 'Brand' })).toBeVisible();
    await user.click(within(sheet.getByRole('group', { name: 'Condition' })).getByRole('button', { name: 'Used (1)' }));
    await user.click(sheet.getByRole('button', { name: 'Show drives' }));
    expect(screen.queryByRole('dialog', { name: 'Filters' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Filters (4)' })).toBeVisible();
  } finally { delete (window as Partial<Window>).matchMedia; }
});

it('marks each filter that is set, so it reads apart from those left at Any', () => {
  render(<MantineProvider env="test"><ListingFilters query={{ ...defaultQuery(), media_type: 'hdd' }} recentDays={7} stores={knownStores}
    capacities={[]} brands={[]} conditions={[]} onChange={() => {}} /></MantineProvider>);
  expect(screen.getByLabelText('Media type').closest('.filter-set')).not.toBeNull();
  expect(screen.getByLabelText('Interface').closest('.filter-set')).toBeNull();
});
