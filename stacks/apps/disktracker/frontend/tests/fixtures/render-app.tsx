import { render, screen, within } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { App } from '../../src/App';
import type { Offer, DisktrackerApi, ReviewItem } from '../../src/api';
import { detailOf, drivePage, pricesOf, rowsOf } from './responses';
import { groupKeyFor } from '../../src/drive-groups';
import { checkedAt, knownKinds, knownStores, shoppingListings, unusedWrites } from './listings';

export type FakeApi = Omit<Partial<DisktrackerApi>, 'listOffers' | 'reviewItems'> & {
  listOffers?: () => Promise<Offer[]>;
  /** The whole review queue; like the server, the fake serves it a page at a time, of one store
   * or for one reason when asked. */
  reviewItems?: () => Promise<ReviewItem[]>;
};

/** Whether an offer is of the drive an id names: a drive's, or for an offer of no drive, its own. */
export const ofDrive = (id: string) => (offer: Offer) => [`drive:${id}`, `listing:${id}`].includes(groupKeyFor(offer));

/** Stands in for the browser's localStorage. */
export function memoryStorage(): Pick<Storage, 'getItem' | 'setItem'> {
  const values = new Map<string, string>();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => { values.set(key, value); } };
}

export function renderApp({ listOffers = async () => shoppingListings, reviewItems = async () => [], ...overrides }: FakeApi = {}, base = '/', storage = memoryStorage()) {
  const api: DisktrackerApi = {
    ...unusedWrites,
    reviewItems: async ({ limit, offset, store, reason }) => {
      const queued = (await reviewItems()).filter(item => (!store || item.store === store) && (!reason || item.reason === reason));
      return { items: queued.slice(offset, offset + limit), total: queued.length };
    },
    latestRuns: async () => [],
    recentRuns: async () => [],
    // A collector heard from just now, running nothing, with nothing waiting.
    collectorStatus: async () => ({ seen_at: checkedAt.toISOString(), running: [], waiting: [] }),
    listSources: async () => knownStores,
    listSourceKinds: async () => knownKinds,
    listConditionRules: async () => [],
    // The offers as the server would list them, unfiltered, a page at a time; a drive and its prices
    // by the drive. A test that filters says what the server answers.
    drives: async query => drivePage(rowsOf(await listOffers()), {}, query),
    drive: async id => detailOf((await listOffers()).filter(ofDrive(id))),
    offer: async id => {
      const found = (await listOffers()).find(offer => offer.id === id);
      if (!found) throw new Error('Offer not found');
      return found;
    },
    prices: async request => pricesOf((await listOffers()).filter(ofDrive(request.driveId ?? '')), request),
    offersToRecheck: async () => [],
    pricesToday: async () => [],
    ...overrides,
    listOffers: async () => (await listOffers()).map(({ observations: _history, ...summary }) => summary),
  };
  return render(<MantineProvider env="test"><App api={api} base={base} storage={storage}
    now={() => checkedAt} nextId={() => 'save-key'} /></MantineProvider>);
}

/** Which drives a table lists, in order: each row by the store title of the offer it is shown by,
 * as its button's tooltip gives it (drives are named alike; their offers are not). */
export function namesIn(table: string) {
  return within(screen.getByRole('table', { name: table })).getAllByRole('row').slice(1)
    .map(row => within(row).getAllByRole('button')[0].getAttribute('title'));
}
