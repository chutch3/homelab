import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { DeletePriceDialog } from '../../src/DeletePriceDialog';
import type { ListingsApi } from '../../src/api';
import { historyPrices, makeListing, unusedWrites } from '../fixtures/listings';

afterEach(cleanup);

function renderDialog(listing: ReturnType<typeof makeListing>, deletePrice: ListingsApi['deletePrice']) {
  const handlers = { onClose: vi.fn(), onDeleted: vi.fn(async () => {}) };
  render(<MantineProvider env="test"><DeletePriceDialog listing={listing} observation={listing.observations[0]}
    api={{ ...unusedWrites, deletePrice }} {...handlers} /></MantineProvider>);
  return { handlers, dialog: within(screen.getByRole('dialog', { name: 'Delete price' })) };
}

it('names the price being deleted, deletes it, then reports and closes', async () => {
  const user = userEvent.setup();
  const listing = makeListing('h', { store: 'goharddrive', seller: '', observations: historyPrices, latest: historyPrices[1] });
  const deletePrice = vi.fn<ListingsApi['deletePrice']>(async () => listing);
  const { handlers, dialog } = renderDialog(listing, deletePrice);
  expect(dialog.getByText(/\$220\.00 from GoHardDrive/)).toBeVisible();
  expect(dialog.queryByText(/offer is removed too/)).not.toBeInTheDocument();
  await user.click(dialog.getByRole('button', { name: 'Delete' }));
  expect(deletePrice).toHaveBeenCalledWith('h', 'previous');
  expect(handlers.onDeleted).toHaveBeenCalled();
  expect(handlers.onClose).toHaveBeenCalled();
});

it('warns that deleting the only price removes the offer, and keeps the dialog open on failure', async () => {
  const user = userEvent.setup();
  const listing = makeListing('only');
  const { handlers, dialog } = renderDialog(listing, async () => { throw new Error('Connection lost. Try again.'); });
  expect(dialog.getByText(/only price, so the offer is removed too/)).toBeVisible();
  await user.click(dialog.getByRole('button', { name: 'Delete' }));
  expect(await dialog.findByRole('alert')).toHaveTextContent('Connection lost. Try again.');
  expect(handlers.onClose).not.toHaveBeenCalled();
});
