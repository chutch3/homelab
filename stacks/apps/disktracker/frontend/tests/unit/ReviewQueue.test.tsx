import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { ReviewQueue } from '../../src/ReviewQueue';
import type { DisktrackerApi, ReviewItem } from '../../src/api';
import { knownStores, makeDrive, makeOffer, makeReviewItem, unusedWrites } from '../fixtures/listings';
import { memoryStorage } from '../fixtures/render-app';
import { foundPage, rowsOf } from '../fixtures/responses';

afterEach(cleanup);

/** The queue as the API serves it, a page at a time; failing first with `failure`, when given. */
async function renderQueue(items: ReviewItem[], api: Partial<DisktrackerApi> = {}, failure = '') {
  const handlers = { onChanged: vi.fn(async () => {}) };
  let failing = failure;
  const reviewItems: DisktrackerApi['reviewItems'] = async ({ limit, offset }) => {
    if (failing) { const message = failing; failing = ''; throw new Error(message); }
    return { items: items.slice(offset, offset + limit), total: items.length };
  };
  render(<MantineProvider env="test"><ReviewQueue api={{ ...unusedWrites, reviewItems, ...api }} storage={memoryStorage()}
    stores={knownStores} all={items.length} revision={0} {...handlers} /></MantineProvider>);
  const review = within(screen.getByRole('region', { name: /Needs matching/ }));
  await waitFor(() => expect(review.queryByRole('status', { name: 'Loading offers to match' })).not.toBeInTheDocument());
  return { handlers, review, user: userEvent.setup() };
}

it('explains why each offer is waiting, with its store, its link and its price', async () => {
  const { review } = await renderQueue([
    makeReviewItem('a', { title: 'Mystery drive', reason: 'missing_mpn', item_price_cents: 36999 }),
    makeReviewItem('b', { reason: 'missing_condition' }),
    makeReviewItem('c', { reason: 'capacity_conflict' }),
    makeReviewItem('d', { reason: 'missing_capacity' }),
    makeReviewItem('e', { reason: 'missing_price', item_price_cents: null }),
  ]);
  const rows = review.getAllByRole('row').slice(1);
  expect(rows.map(row => within(row).getAllByRole('cell')[1].textContent)).toEqual([
    'No MPN', 'Unknown condition', 'Capacity mismatch', 'Needs capacity', 'No price yet',
  ]);
  expect(within(rows[0]).getByRole('link', { name: 'Mystery drive' })).toHaveAttribute('href', 'https://www.serverpartdeals.com/products/a');
  expect(within(rows[0]).getByText('$369.99')).toBeVisible();
  expect(within(rows[0]).getAllByRole('cell')[3]).toHaveTextContent('ServerPartDeals');
  expect(review.getByRole('heading', { name: 'Needs matching (5)' })).toBeVisible();
  expect(within(rows[4]).getByText('—')).toBeVisible();
});

it('ignores an offer only once that is confirmed, and says when nothing is left', async () => {
  const decide = vi.fn<DisktrackerApi['decide']>(async () => ({ status: 'ignored', offer_id: null }));
  const { review, user, handlers } = await renderQueue([makeReviewItem('a')], { decide });
  await user.click(review.getByRole('button', { name: 'Ignore' }));
  expect(review.getByText('Ignore this offer? Later collections skip its page too.')).toBeVisible();
  expect(review.queryByRole('button', { name: 'Resolve' })).not.toBeInTheDocument();
  expect(decide).not.toHaveBeenCalled();
  await user.click(review.getByRole('button', { name: 'Keep' }));
  expect(review.getByRole('button', { name: 'Resolve' })).toBeVisible();
  await user.click(review.getByRole('button', { name: 'Ignore' }));
  await user.click(review.getByRole('button', { name: 'Yes, ignore' }));
  expect(decide).toHaveBeenCalledWith('a', { decision: 'ignore' });
  expect(handlers.onChanged).toHaveBeenCalled();
  cleanup();
  await renderQueue([]);
  // Said as the other list says it is clear: in words, with no tick before them.
  expect(screen.getByText('Nothing to match.')).toHaveTextContent(/^Nothing to match\.$/);
});

it('says the offers could not be loaded instead of that there are none, with a way to try again', async () => {
  const { review, user } = await renderQueue([makeReviewItem('waiting')], {}, 'Unable to save or load listings (503).');
  expect(review.getByRole('alert')).toHaveTextContent('The offers to match could not be loaded: Unable to save or load listings (503).');
  expect(review.queryByText('Nothing to match.')).not.toBeInTheDocument();
  await user.click(review.getByRole('button', { name: 'Try again' }));
  expect(await review.findByRole('link', { name: 'waiting' })).toBeVisible();
  expect(review.queryByRole('alert')).not.toBeInTheDocument();
});

it('resolves an offer with the details the scraper found filled in, making the drive it names first', async () => {
  const decide = vi.fn<DisktrackerApi['decide']>(async () => ({ status: 'matched', offer_id: 'x' }));
  const createDrive = vi.fn<DisktrackerApi['createDrive']>(async () => makeDrive('ST18000NM000J'));
  const item = makeReviewItem('a', { mpn: 'ST18000NM000J', condition: null, capacity_gb: 18000, reason: 'missing_condition' });
  const { review, user, handlers } = await renderQueue([item], { decide, createDrive });
  await user.click(review.getByRole('button', { name: 'Resolve' }));
  const form = within(screen.getByRole('dialog', { name: 'Resolve offer' }));
  expect(form.getByRole('textbox', { name: 'Drive' })).toHaveValue('ST18000NM000J');
  expect(form.getByLabelText('Capacity', { exact: true })).toHaveValue('18000');
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(form.getByLabelText('Condition', { exact: true })).toHaveAccessibleDescription(expect.stringContaining('Choose a condition.'));
  await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'used');
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(createDrive).toHaveBeenCalledWith({ mpn: 'ST18000NM000J', capacity_gb: 18000 });
  expect(decide).toHaveBeenCalledWith('a', { decision: 'match', drive_id: 'drive-ST18000NM000J', condition: 'used' });
  expect(handlers.onChanged).toHaveBeenCalled();
});

it('refuses a capacity for a typed MPN recorded at another, and decides nothing', async () => {
  const decide = vi.fn<DisktrackerApi['decide']>(async () => ({ status: 'matched', offer_id: 'x' }));
  const drive = makeDrive('ST18000NM000J');
  // Not chosen from the suggestions: found only as the decision is saved.
  const findDrives = vi.fn<DisktrackerApi['findDrives']>(async () => foundPage(rowsOf([makeOffer('Exos X18', { drive, mpn: drive.mpn })])));
  const item = makeReviewItem('a', { mpn: null, condition: 'new', capacity_gb: 20000 });
  const { review, user } = await renderQueue([item], { decide, findDrives });
  await user.click(review.getByRole('button', { name: 'Resolve' }));
  const form = within(screen.getByRole('dialog', { name: 'Resolve offer' }));
  await user.type(form.getByRole('textbox', { name: 'Drive' }), 'ST18000NM000J');
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(await form.findByText('ST18000NM000J is recorded as 18 TB. Choose it to record the offer as that drive.')).toBeVisible();
  expect(decide).not.toHaveBeenCalled();
});

it('keeps the resolve form open and explains a server rejection', async () => {
  const decide = vi.fn(async () => { throw new Error('Drive not found.'); });
  const drive = makeDrive('ST18000NM000J', { capacity_gb: 20000 });
  const { review, user } = await renderQueue([makeReviewItem('a', { mpn: 'ST18000NM000J', condition: 'new', capacity_gb: 20000, drive })], { decide });
  await user.click(review.getByRole('button', { name: 'Resolve' }));
  const form = within(screen.getByRole('dialog', { name: 'Resolve offer' }));
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(await form.findByRole('alert')).toHaveTextContent('Drive not found.');
});

it('asks for the last page there is, worked out from the total, when the one shown is left empty', async () => {
  let queue = Array.from({ length: 120 }, (_, index) => makeReviewItem(`queued-${index + 1}`));
  const asked: number[] = [];
  const reviewItems = vi.fn<DisktrackerApi['reviewItems']>(async ({ limit, offset }) => {
    asked.push(offset);
    return { items: queue.slice(offset, offset + limit), total: queue.length };
  });
  const queueAt = (revision: number) => <MantineProvider env="test"><ReviewQueue api={{ ...unusedWrites, reviewItems }} storage={memoryStorage()}
    stores={knownStores} all={queue.length} revision={revision} onChanged={async () => {}} /></MantineProvider>;
  const { rerender } = render(queueAt(0));
  const pages = within(await screen.findByRole('navigation', { name: 'Needs matching pages' }));
  const user = userEvent.setup();
  await user.click(pages.getByRole('button', { name: 'Next page' }));
  await user.click(pages.getByRole('button', { name: 'Next page' }));
  expect(await pages.findByText('101–120 of 120')).toBeVisible();
  queue = queue.slice(0, 30);
  asked.length = 0;
  rerender(queueAt(1));
  expect(await pages.findByText('1–30 of 30')).toBeVisible();
  expect(asked).toEqual([100, 0]);
});

it('says which MPN the page named that another drive already goes by', async () => {
  const item = makeReviewItem('conflict', { reason: 'alias_conflict', mpn: 'ST16000NM000J', condition: 'new',
    aliases: ['0XYZ'], conflict_mpn: '0XYZ', conflict_drive_id: 'other-drive' });
  const { review, user } = await renderQueue([item]);
  expect(within(review.getAllByRole('row')[1]).getAllByRole('cell')[1]).toHaveTextContent('MPN of another drive');
  await user.click(review.getByRole('button', { name: 'Resolve' }));
  const form = within(screen.getByRole('dialog', { name: 'Resolve offer' }));
  expect(form.getByText('The store also calls it 0XYZ, which another drive already goes by. Nothing it said was recorded.')).toBeVisible();
});
