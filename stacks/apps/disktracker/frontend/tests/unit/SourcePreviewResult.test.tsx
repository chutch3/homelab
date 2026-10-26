import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { SourcePreviewResult } from '../../src/SourcePreviewResult';
import type { SourcePreview } from '../../src/api';

afterEach(cleanup);

const offer = {
  url: 'https://store.test/x18', title: 'Seagate Exos X18 18TB', mpn: 'ST18000NM000J', brand: 'Seagate',
  condition: 'new', capacity_gb: 18000, item_price_cents: 30000, shipping_cents: 0, in_stock: true, aliases: [],
};
const said = (verdict: SourcePreview['verdict']) => {
  render(<MantineProvider env="test"><SourcePreviewResult preview={{ status: 'found', reason: null, offer, verdict, notes: [] }} /></MantineProvider>);
  const text = screen.getByRole('alert').textContent;
  cleanup();
  return text;
};

it('says in a sentence what taking the offer in would do, for each reason', () => {
  expect(said({ outcome: 'recorded', reason: null })).toBe('It would be recorded.');
  expect(said({ outcome: 'ignored', reason: 'sold_out' })).toBe('It is sold out and has never had a price, so nothing would be recorded until it is in stock.');
  expect(said({ outcome: 'ignored', reason: 'decided' })).toBe('A reviewer said this listing is nothing to track, so it would be ignored.');
  expect(said({ outcome: 'review', reason: 'missing_mpn' })).toBe('It would wait under Needs matching: no MPN was read.');
  expect(said({ outcome: 'review', reason: 'not_a_single_drive' })).toBe('It would wait under Needs matching: its title reads as several drives, tape or other equipment.');
  expect(said({ outcome: 'review', reason: 'implausible_capacity' })).toBe('It would wait under Needs matching: the capacity it gives is more than any drive holds, or not what its title says.');
  expect(said({ outcome: 'review', reason: 'alias_conflict' })).toBe('It would wait under Needs matching: it names an MPN another drive already goes by.');
});
