import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { OfferForm } from '../../src/OfferForm';
import type { ListingsApi } from '../../src/api';
import { makeListing, unusedWrites } from '../fixtures/listings';

afterEach(cleanup);

const listing = makeListing('offer', { title: 'Exos X18', mpn: 'ST18000NM000J', store: 'serverpartdeals', seller: '',
  condition: 'refurbished', url: 'https://example.com/x18', capacity_gb: 18000 });

function renderForm(editOffer: ListingsApi['editOffer']) {
  const handlers = { onClose: vi.fn(), onSaved: vi.fn(async () => {}) };
  render(<MantineProvider env="test"><OfferForm listing={listing} api={{ ...unusedWrites, editOffer }} {...handlers} /></MantineProvider>);
  return { handlers, form: within(screen.getByRole('dialog', { name: 'Edit offer' })), user: userEvent.setup() };
}

it("saves changed details in place and shows the offer's fixed identity", async () => {
  const editOffer = vi.fn<ListingsApi['editOffer']>(async () => listing);
  const { handlers, form, user } = renderForm(editOffer);
  expect(form.getByText('ST18000NM000J · ServerPartDeals · Refurbished')).toBeVisible();
  expect(form.getByRole('textbox', { name: 'Offer title' })).toHaveValue('Exos X18');
  const url = form.getByRole('textbox', { name: 'Store page URL' });
  await user.clear(url);
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(form.queryByLabelText('Capacity', { exact: true })).not.toBeInTheDocument();
  expect(editOffer).toHaveBeenCalledWith('offer', { title: 'Exos X18', url: null });
  expect(handlers.onSaved).toHaveBeenCalled();
  expect(handlers.onClose).toHaveBeenCalled();
});

it('validates before saving and keeps the form open when the server rejects it', async () => {
  const { handlers, form, user } = renderForm(async () => { throw new Error('Connection lost. Try again.'); });
  const title = form.getByRole('textbox', { name: 'Offer title' });
  await user.clear(title);
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(title).toHaveAccessibleDescription(expect.stringContaining('Enter the offer title.'));
  await user.type(title, 'Exos X18');
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(await form.findByRole('alert')).toHaveTextContent('Connection lost. Try again.');
  expect(handlers.onClose).not.toHaveBeenCalled();
});
