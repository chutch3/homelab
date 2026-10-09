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
  expect(changed).toMatchObject({ search: 'Exos', capacities: ['18000'], conditions: ['new', 'used'], stores: ['goharddrive'], recentOnly: true, inStockOnly: true });
  expect(screen.getByLabelText('Active filters')).toHaveTextContent('GoHardDrive');
  expect(screen.getByLabelText('Active filters')).toHaveTextContent('18 TB');
  expect(screen.getByLabelText('Active filters')).toHaveTextContent('In stock only');
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
