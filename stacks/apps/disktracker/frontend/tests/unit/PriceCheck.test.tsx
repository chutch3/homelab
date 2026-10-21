import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { PriceCheck } from '../../src/PriceCheck';
import type { DisktrackerApi, PriceResult } from '../../src/api';
import { makeOffer, recordedOn, unusedWrites } from '../fixtures/listings';

afterEach(cleanup);

const listing = makeOffer('WD Red Plus 12TB', { mpn: 'WD120EFBX', store: 'other', seller: 'Micro Center', url: 'https://store.test/red' },
  { item_price_cents: 20000, shipping_cents: 500, total_cents: 20500 });
// A recheck names the offer it is of: it says nothing of what the offer is.
const identity = { offer_id: listing.id, observed_at: null, notes: '' };

function renderCheck(recordPrice: DisktrackerApi['recordPrice'], props: Partial<Parameters<typeof PriceCheck>[0]> = {}) {
  const onRecorded = vi.fn(async () => {});
  let id = 0;
  render(<MantineProvider env="test"><PriceCheck listing={listing} api={{ ...unusedWrites, recordPrice }}
    nextId={() => `key-${id += 1}`} onRecorded={onRecorded} {...props} /></MantineProvider>);
  return { user: userEvent.setup(), onRecorded };
}

it('records no change, a new price or out of stock in one step each, keeping the shipping last recorded', async () => {
  const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn(listing));
  const { user, onRecorded } = renderCheck(recordPrice);
  expect(screen.getByRole('link', { name: 'Open store ↗' })).toHaveAttribute('href', 'https://store.test/red');
  await user.click(screen.getByRole('button', { name: 'No change' }));
  expect(recordPrice).toHaveBeenLastCalledWith({ ...identity, item_price_cents: 20000, shipping_cents: 500, in_stock: true }, 'key-1');
  expect(onRecorded).toHaveBeenLastCalledWith('Checked WD Red Plus 12TB: no change.');
  await user.type(screen.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' }), '189.99');
  await user.click(screen.getByRole('button', { name: 'Save' }));
  expect(recordPrice).toHaveBeenLastCalledWith({ ...identity, item_price_cents: 18999, shipping_cents: 500, in_stock: true }, 'key-2');
  expect(onRecorded).toHaveBeenLastCalledWith('Recorded $189.99 for WD Red Plus 12TB.');
  expect(screen.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' })).toHaveValue('');
  await user.click(screen.getByRole('button', { name: 'Out of stock' }));
  expect(recordPrice).toHaveBeenLastCalledWith({ ...identity, item_price_cents: null, shipping_cents: 500, in_stock: false }, 'key-3');
  expect(onRecorded).toHaveBeenLastCalledWith('Marked WD Red Plus 12TB out of stock.');
});

it('says what is wrong with a price it cannot read or was not given, and records nothing', async () => {
  const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn(listing));
  const { user } = renderCheck(recordPrice);
  await user.click(screen.getByRole('button', { name: 'Save' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Enter the new price.');
  await user.type(screen.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' }), '18.999{Enter}');
  expect(screen.getByRole('alert')).toHaveTextContent('Enter a non-negative amount with up to two decimal places.');
  await user.clear(screen.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' }));
  await user.type(screen.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' }), '0{Enter}');
  expect(screen.getByRole('alert')).toHaveTextContent('Enter a price above zero.');
  expect(recordPrice).not.toHaveBeenCalled();
});

it('takes no second answer while one is being saved, and keeps a typed price when the save fails', async () => {
  let fail: (error: Error) => void = () => {};
  const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(() => new Promise<PriceResult>((_, reject) => { fail = reject; }));
  const { user, onRecorded } = renderCheck(recordPrice);
  const price = screen.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' });
  await user.type(price, '189.99{Enter}');
  for (const name of ['No change', 'Save', 'Out of stock']) expect(screen.getByRole('button', { name })).toBeDisabled();
  expect(price).toBeDisabled();
  fail(new Error('Connection lost. Try again.'));
  expect(await screen.findByRole('alert')).toHaveTextContent('Connection lost. Try again.');
  expect(price).toHaveValue('189.99');
  expect(screen.getByRole('button', { name: 'No change' })).toBeEnabled();
  expect(recordPrice).toHaveBeenCalledTimes(1);
  expect(onRecorded).not.toHaveBeenCalled();
});

it('leaves out the store page link where the row already has one, and shows what it is given beside the answers', () => {
  renderCheck(vi.fn<DisktrackerApi['recordPrice']>(), { link: false, more: <button>More options</button> });
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'More options' })).toBeVisible();
});

it('says which price it recorded when the answer made a new one, so that it can be taken back', async () => {
  const recorded = { ...listing.latest, id: 'new-price', item_price_cents: 18999, total_cents: 19499 };
  const recordPrice = vi.fn<DisktrackerApi['recordPrice']>(async () => recordedOn(listing, recorded.id));
  const { user, onRecorded } = renderCheck(recordPrice);
  await user.type(screen.getByRole('textbox', { name: 'New price for WD Red Plus 12TB' }), '189.99');
  await user.click(screen.getByRole('button', { name: 'Save' }));
  expect(onRecorded).toHaveBeenLastCalledWith('Recorded $189.99 for WD Red Plus 12TB.', { priceId: 'new-price' });
});
