import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { ReviewQueue } from '../../src/ReviewQueue';
import type { ListingsApi, UnmatchedItem } from '../../src/api';
import { knownStores, makeListing, makeUnmatched, unusedWrites } from '../fixtures/listings';

afterEach(cleanup);

function renderQueue(items: UnmatchedItem[], api: Partial<ListingsApi> = {}, error = '') {
  const handlers = { onChanged: vi.fn(async () => {}), onRetry: vi.fn() };
  render(<MantineProvider env="test"><ReviewQueue items={items} total={items.length} page={0} pageSize={50} onPage={() => {}} onPageSize={() => {}}
    stores={knownStores} error={error} api={{ ...unusedWrites, ...api }} {...handlers} /></MantineProvider>);
  return { handlers, review: within(screen.getByRole('region', { name: /Needs matching/ })), user: userEvent.setup() };
}

it('explains why each offer is waiting, with its store, its link and its price', () => {
  const { review } = renderQueue([
    makeUnmatched('a', { title: 'Mystery drive', reason: 'missing_mpn', item_price_cents: 36999 }),
    makeUnmatched('b', { reason: 'missing_condition' }),
    makeUnmatched('c', { reason: 'capacity_conflict' }),
    makeUnmatched('d', { reason: 'missing_capacity' }),
    makeUnmatched('e', { reason: 'missing_price', item_price_cents: null }),
  ]);
  const rows = review.getAllByRole('row').slice(1);
  expect(rows.map(row => within(row).getAllByRole('cell')[1].textContent)).toEqual([
    'No MPN found', 'Condition not recognized', "Capacity doesn't match the drive", 'New drive needs a capacity', 'No price yet',
  ]);
  expect(within(rows[0]).getByRole('link', { name: 'Mystery drive' })).toHaveAttribute('href', 'https://www.serverpartdeals.com/products/a');
  expect(within(rows[0]).getByText('$369.99')).toBeVisible();
  expect(within(rows[0]).getAllByRole('cell')[3]).toHaveTextContent('ServerPartDeals');
  expect(review.getByRole('heading', { name: 'Needs matching (5)' })).toBeVisible();
  expect(within(rows[4]).getByText('—')).toBeVisible();
});

it('ignores an offer only once that is confirmed, and says when nothing is left', async () => {
  const ignoreUnmatched = vi.fn<ListingsApi['ignoreUnmatched']>(async () => {});
  const { review, user, handlers } = renderQueue([makeUnmatched('a')], { ignoreUnmatched });
  await user.click(review.getByRole('button', { name: 'Ignore' }));
  expect(review.getByText('Ignore this offer?')).toBeVisible();
  expect(review.queryByRole('button', { name: 'Resolve' })).not.toBeInTheDocument();
  expect(ignoreUnmatched).not.toHaveBeenCalled();
  await user.click(review.getByRole('button', { name: 'Keep' }));
  expect(review.getByRole('button', { name: 'Resolve' })).toBeVisible();
  await user.click(review.getByRole('button', { name: 'Ignore' }));
  await user.click(review.getByRole('button', { name: 'Yes, ignore' }));
  expect(ignoreUnmatched).toHaveBeenCalledWith('a');
  expect(handlers.onChanged).toHaveBeenCalled();
  cleanup();
  renderQueue([]);
  expect(screen.getByText('Nothing to match.')).toBeVisible();
});

it('says the offers could not be loaded instead of that there are none, with a way to try again', async () => {
  const { review, user, handlers } = renderQueue([], {}, 'Unable to save or load listings (503).');
  expect(review.getByRole('alert')).toHaveTextContent('The offers to match could not be loaded: Unable to save or load listings (503).');
  expect(review.queryByText('Nothing to match.')).not.toBeInTheDocument();
  await user.click(review.getByRole('button', { name: 'Try again' }));
  expect(handlers.onRetry).toHaveBeenCalled();
});

it('resolves an offer with the details the scraper found filled in', async () => {
  const resolveUnmatched = vi.fn<ListingsApi['resolveUnmatched']>(async () => makeListing('x'));
  const item = makeUnmatched('a', { mpn: 'ST18000NM000J', condition: null, capacity_gb: 18000, reason: 'missing_condition' });
  const { review, user, handlers } = renderQueue([item], { resolveUnmatched });
  await user.click(review.getByRole('button', { name: 'Resolve' }));
  const form = within(screen.getByRole('dialog', { name: 'Resolve offer' }));
  expect(form.getByRole('textbox', { name: 'MPN' })).toHaveValue('ST18000NM000J');
  expect(form.getByLabelText('Capacity', { exact: true })).toHaveValue('18000');
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(form.getByLabelText('Condition', { exact: true })).toHaveAccessibleDescription(expect.stringContaining('Choose a condition.'));
  await user.selectOptions(form.getByLabelText('Condition', { exact: true }), 'used');
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(resolveUnmatched).toHaveBeenCalledWith('a', { mpn: 'ST18000NM000J', condition: 'used', capacity_gb: 18000 });
  expect(handlers.onChanged).toHaveBeenCalled();
});

it('keeps the resolve form open and explains a server rejection', async () => {
  const resolveUnmatched = vi.fn(async () => { throw new Error('MPN ST18000NM000J is recorded as 18 TB.'); });
  const { review, user } = renderQueue([makeUnmatched('a', { mpn: 'ST18000NM000J', condition: 'new', capacity_gb: 20000 })], { resolveUnmatched });
  await user.click(review.getByRole('button', { name: 'Resolve' }));
  const form = within(screen.getByRole('dialog', { name: 'Resolve offer' }));
  await user.click(form.getByRole('button', { name: 'Save' }));
  expect(await form.findByRole('alert')).toHaveTextContent('MPN ST18000NM000J is recorded as 18 TB.');
});
