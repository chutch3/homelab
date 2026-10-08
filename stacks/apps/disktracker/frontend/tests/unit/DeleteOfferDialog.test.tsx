import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { DeleteOfferDialog } from '../../src/DeleteOfferDialog';
import type { ListingsApi } from '../../src/api';
import { historyPrices, makeListing, unusedWrites } from '../fixtures/listings';

afterEach(cleanup);

const listing = makeListing('offer', { title: 'Exos X18', store: 'goharddrive', seller: '', condition: 'refurbished',
  observations: historyPrices, latest: historyPrices[1] });

function renderDialog(deleteOffer: ListingsApi['deleteOffer']) {
  const handlers = { onClose: vi.fn(), onDeleted: vi.fn(async () => {}) };
  render(<MantineProvider env="test"><DeleteOfferDialog listing={listing} api={{ ...unusedWrites, deleteOffer }} {...handlers} /></MantineProvider>);
  return { handlers, dialog: within(screen.getByRole('dialog', { name: 'Delete offer' })), user: userEvent.setup() };
}

it('names the offer and how many prices go with it, then deletes it', async () => {
  const deleteOffer = vi.fn<ListingsApi['deleteOffer']>(async () => {});
  const { handlers, dialog, user } = renderDialog(deleteOffer);
  expect(dialog.getByText(/Exos X18 · GoHardDrive · Refurbished and its 2 prices/)).toBeVisible();
  await user.click(dialog.getByRole('button', { name: 'Delete' }));
  expect(deleteOffer).toHaveBeenCalledWith('offer');
  expect(handlers.onDeleted).toHaveBeenCalled();
  expect(handlers.onClose).toHaveBeenCalled();
});

it('keeps the dialog open and explains a failure', async () => {
  const { handlers, dialog, user } = renderDialog(async () => { throw new Error('Connection lost. Try again.'); });
  await user.click(dialog.getByRole('button', { name: 'Delete' }));
  expect(await dialog.findByRole('alert')).toHaveTextContent('Connection lost. Try again.');
  expect(handlers.onClose).not.toHaveBeenCalled();
});
