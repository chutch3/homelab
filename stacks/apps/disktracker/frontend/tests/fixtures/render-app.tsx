import { render, screen, within } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { App } from '../../src/App';
import type { Listing, ListingsApi, UnmatchedItem } from '../../src/api';
import { checkedAt, knownKinds, knownStores, shoppingListings, unusedWrites } from './listings';

export type FakeApi = Omit<Partial<ListingsApi>, 'list' | 'listUnmatched'> & {
  list?: () => Promise<Listing[]>;
  /** The whole review queue; like the server, the fake serves it a page at a time. */
  listUnmatched?: () => Promise<UnmatchedItem[]>;
};

/** Like the server, the list carries each offer's latest price; its history comes from priceHistory. */
/** Stands in for the browser's localStorage. */
export function memoryStorage(): Pick<Storage, 'getItem' | 'setItem'> {
  const values = new Map<string, string>();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => { values.set(key, value); } };
}

export function renderApp({ list = async () => shoppingListings, listUnmatched = async () => [], ...overrides }: FakeApi = {}, base = '/', storage = memoryStorage()) {
  const api: ListingsApi = {
    ...unusedWrites,
    listUnmatched: async ({ limit, offset }) => {
      const queued = await listUnmatched();
      return { items: queued.slice(offset, offset + limit), total: queued.length };
    },
    latestRuns: async () => [],
    // A collector heard from just now, running nothing, with nothing waiting.
    collectorStatus: async () => ({ seen_at: checkedAt.toISOString(), running: [], waiting: [] }),
    listSources: async () => knownStores,
    listSourceKinds: async () => knownKinds,
    listConditionRules: async () => [],
    priceHistory: async ids => (await list()).filter(listing => ids.includes(listing.id)),
    ...overrides,
    list: async () => (await list()).map(({ observations: _history, ...summary }) => summary),
  };
  return render(<MantineProvider env="test"><App api={api} base={base} storage={storage}
    now={() => checkedAt} nextId={() => 'save-key'} /></MantineProvider>);
}

/** The drive names a table lists, in order: each row's button. */
export function namesIn(table: string) {
  return within(screen.getByRole('table', { name: table })).getAllByRole('row').slice(1)
    .map(row => within(row).getAllByRole('button')[0].textContent);
}
