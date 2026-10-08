import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { knownStores, unusedWrites } from '../fixtures/listings';
import { EntryForm } from '../../src/EntryForm';
import { ApiValidationError, type Listing, type ListingsApi } from '../../src/api';

afterEach(cleanup);

const observation = {
  id: 'observation', item_price_cents: 18000, shipping_cents: 0, shipping_known: true, in_stock: true,
  observed_at: '2026-09-21T12:00:00Z', notes: '',
  entered_at: '2026-09-21T12:00:00Z', acquisition_method: 'manual' as const,
  total_cents: 18000, price_per_tb: '10.00',
};
const listing: Listing = {
  drive: null,
  id: 'listing', title: 'Example drive', mpn: 'ST18000NM000J', store: 'other', store_name: 'Other', seller: 'Example seller', url: 'https://example.com/d',
  capacity_gb: 18000, condition: 'refurbished', last_checked_at: observation.observed_at, latest: observation, observations: [observation],
};

function renderForm(failure: Error) {
  const api: ListingsApi = {
    ...unusedWrites,
    list: async () => [listing],
    recordPrice: async () => { throw failure; },
  };
  render(<MantineProvider env="test"><EntryForm stores={knownStores} api={api} listing={listing}
    now={() => new Date('2026-09-21T12:00:00Z')} nextId={() => 'save-key'}
    onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
  return userEvent.setup();
}

describe('EntryForm', () => {
  it('records the first price for a new offer, requiring its MPN, store, condition, and item price', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    const onSaved = vi.fn(async () => {});
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={{ ...unusedWrites, recordPrice }} listing={null}
      now={() => new Date('2026-09-21T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={onSaved} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(form.getByLabelText('Item price (USD)', { exact: true })).toHaveAccessibleDescription(expect.stringContaining('Enter the item price.'));
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '299.99');
    expect(form.getByRole('textbox', { name: 'MPN' })).toHaveAccessibleDescription(expect.stringContaining('Enter the MPN.'));
    expect(form.getByLabelText('Condition', { exact: true })).toHaveAccessibleDescription(expect.stringContaining('Choose a condition.'));
    expect(form.getByLabelText('Store', { exact: true })).toHaveAccessibleDescription(expect.stringContaining('Choose a store.'));
    expect(recordPrice).not.toHaveBeenCalled();
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'serverpartdeals');
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'manufacturer_recertified');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(recordPrice).toHaveBeenCalledWith({
      mpn: 'ST20000NM007D', store: 'serverpartdeals', seller: '', condition: 'manufacturer_recertified',
      title: null, url: null, capacity_gb: 20000, item_price_cents: 29999, shipping_cents: 0, in_stock: true,
      observed_at: null, notes: '',
    }, 'save-key');
    expect(onSaved).toHaveBeenCalledWith('listing', observation.observed_at);
  }, 15000);

  it('offers standard capacities, with Other for an unusual size', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={{ ...unusedWrites, recordPrice }} listing={null}
      now={() => new Date('2026-09-21T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    const sizes = within(form.getByLabelText('Capacity', { exact: true })).getAllByRole('option').map(option => option.textContent);
    expect(sizes).toEqual(['Choose capacity', '32 GB', '64 GB', '128 GB', '256 GB', '512 GB', '1 TB', '2 TB', '3 TB', '4 TB',
      '6 TB', '8 TB', '10 TB', '12 TB', '14 TB', '16 TB', '18 TB', '20 TB', '22 TB', '24 TB', '26 TB', '28 TB', '30 TB', '32 TB', 'Other']);
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), 'other');
    await user.type(form.getByLabelText('Other capacity (GB)', { exact: true }), '1500');
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'X5');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '60');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'used');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({ capacity_gb: 1500 }), 'save-key');
  }, 15000);

  it("shows a known MPN's recorded capacity instead of asking for it", async () => {
    const user = userEvent.setup();
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={unusedWrites} listing={null} knownCapacities={{ ST18000NM000J: 18000 }}
      now={() => new Date('2026-09-21T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST18000NM000J');
    expect(form.queryByLabelText('Capacity', { exact: true })).not.toBeInTheDocument();
    expect(form.getByText('18 TB, as recorded for this drive')).toBeVisible();
  });

  it('records the price as observed now unless another date is chosen', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={{ ...unusedWrites, recordPrice }} listing={listing}
      now={() => new Date('2026-09-22T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    expect(form.queryByLabelText('Checked at (local time)')).not.toBeInTheDocument();
    await user.click(form.getByText('More details'));
    await user.click(form.getByRole('button', { name: 'Change date' }));
    const observed = form.getByLabelText('Checked at (local time)', { exact: true });
    await user.clear(observed);
    await user.type(observed, '2026-09-20T08:30');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '170');
    await user.type(form.getByLabelText('Shipping & fees (USD)', { exact: true }), '12.50');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({
      item_price_cents: 17000, shipping_cents: 1250, observed_at: new Date('2026-09-20T08:30').toISOString(),
    }), 'save-key');
  });

  it('lets an existing offer be marked out of stock without a new price, but not a new offer', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={{ ...unusedWrites, recordPrice }} listing={listing}
      now={() => new Date('2026-09-22T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    expect(form.getByRole('radio', { name: 'In stock' })).toBeChecked();
    await user.click(form.getByRole('radio', { name: 'Out of stock' }));
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({ in_stock: false, item_price_cents: null }), 'save-key');
    cleanup();
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={unusedWrites} listing={null}
      now={() => new Date('2026-09-22T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const newOffer = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.click(newOffer.getByRole('radio', { name: 'Out of stock' }));
    await user.click(newOffer.getByRole('button', { name: 'Save offer' }));
    expect(newOffer.getByLabelText('Item price (USD)', { exact: true })).toHaveAccessibleDescription(expect.stringContaining('Enter the item price.'));
  });

  it('asks for a store name only for Other, and drops one typed before choosing a supported store', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={{ ...unusedWrites, recordPrice }} listing={null}
      now={() => new Date('2026-09-21T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    expect(form.queryByRole('textbox', { name: 'Seller name' })).not.toBeInTheDocument();
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'other');
    await user.type(form.getByRole('textbox', { name: 'Seller name' }), 'Some shop');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    expect(form.queryByRole('textbox', { name: 'Seller name' })).not.toBeInTheDocument();
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'refurbished');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(recordPrice).toHaveBeenCalledWith(expect.objectContaining({ store: 'goharddrive', seller: '' }), 'save-key');
  }, 15000);

  it('opens More details to show a field the server rejected there', async () => {
    const user = userEvent.setup();
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => { throw new ApiValidationError({ notes: 'Notes were rejected.' }); });
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={{ ...unusedWrites, recordPrice }} listing={null}
      now={() => new Date('2026-09-21T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.type(form.getByRole('textbox', { name: 'MPN' }), 'ST20000NM007D');
    await user.selectOptions(form.getByLabelText('Capacity', { exact: true }), '20000');
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'goharddrive');
    await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'new');
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '250');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    const notes = await form.findByLabelText('Notes');
    expect(notes.closest('details')).toHaveAttribute('open');
    expect(notes).toHaveFocus();
  }, 15000);

  it('requires a seller name when the store is Other', async () => {
    const user = userEvent.setup();
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={unusedWrites} listing={null}
      now={() => new Date('2026-09-21T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const form = within(screen.getByRole('dialog', { name: 'Add offer' }));
    await user.selectOptions(form.getByLabelText('Store', { exact: true }), 'other');
    await user.click(form.getByRole('button', { name: 'Save offer' }));
    expect(form.getByRole('textbox', { name: 'Seller name' })).toHaveAccessibleDescription(expect.stringContaining('Name the seller when the store is Other.'));
  });

  it("records a later price for an existing offer under that offer's identity", async () => {
    const recordPrice = vi.fn<ListingsApi['recordPrice']>(async () => listing);
    render(<MantineProvider env="test"><EntryForm stores={knownStores} api={{ ...unusedWrites, recordPrice }} listing={listing}
      now={() => new Date('2026-09-22T12:00:00Z')} nextId={() => 'save-key'}
      onClose={() => {}} onSaved={async () => {}} /></MantineProvider>);
    const user = userEvent.setup();
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '170');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(recordPrice).toHaveBeenCalledWith({
      mpn: 'ST18000NM000J', store: 'other', seller: 'Example seller', condition: 'refurbished',
      title: 'Example drive', url: 'https://example.com/d', capacity_gb: null, item_price_cents: 17000,
      shipping_cents: 0, in_stock: true, observed_at: null, notes: '',
    }, 'save-key');
  });

  it('shows Record price API errors on the field, preserves input, and focuses it', async () => {
    const user = renderForm(new ApiValidationError({ shipping_cents: 'Shipping was rejected.' }));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    await user.type(form.getByLabelText('Item price (USD)', { exact: true }), '175');
    const shipping = form.getByLabelText('Shipping & fees (USD)', { exact: true });
    await user.type(shipping, '10');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    await waitFor(() => expect(shipping).toHaveAccessibleDescription(expect.stringContaining('Shipping was rejected.')));
    expect(shipping).toHaveFocus();
    expect(shipping).toHaveValue('10');
    expect(form.getByLabelText('Item price (USD)', { exact: true })).toHaveValue('175');
  });

  it('waits until blur to validate and keeps network failures at form level', async () => {
    const user = renderForm(new Error('Connection lost. Try again.'));
    const form = within(screen.getByRole('dialog', { name: 'Record price' }));
    const item = form.getByLabelText('Item price (USD)', { exact: true });
    await user.type(item, '-');
    expect(item).toHaveAttribute('aria-invalid', 'false');
    await user.tab();
    expect(item).toHaveAttribute('aria-invalid', 'true');
    await user.clear(item);
    await user.type(item, '175');
    await user.click(form.getByRole('button', { name: 'Save price' }));
    expect(await form.findByRole('alert')).toHaveTextContent('Connection lost. Try again.');
    expect(item).toHaveValue('175');
  });
});
