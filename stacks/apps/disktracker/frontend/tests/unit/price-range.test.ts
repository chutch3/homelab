import { describe, expect, it } from 'vitest';
import type { Offer, Observation } from '../../src/api';
import { priceSeries } from '../../src/price-range';
import examples from '../../../tests/examples/lowest-prices.json';
import { checkedAt, makeOffer } from '../fixtures/listings';

const DAY = 86_400_000;
const ago = (days: number) => new Date(checkedAt.getTime() - days * DAY).toISOString();
const price = (id: string, daysAgo: number, item: number, fields: Partial<Observation> = {}): Observation =>
  ({ ...makeOffer(id).latest, id, observed_at: ago(daysAgo), entered_at: ago(daysAgo), item_price_cents: item, total_cents: item, ...fields });
/** An offer with these prices, oldest first, last checked just now unless told otherwise. */
const offer = (id: string, prices: Observation[], lastCheckedDaysAgo = 0): Offer =>
  makeOffer(id, { observations: prices, last_checked_at: ago(lastCheckedDaysAgo) }, prices[prices.length - 1]);

describe("a drive's price series over a period", () => {
  const at = (days: number) => checkedAt.getTime() - days * DAY;

  it('steps through the lowest item price at any store, naming the store that had it and since when, beside each store\'s own steps', () => {
    const spd = offer('spd', [price('spd-1', 60, 20000), price('spd-2', 20, 18000)]);
    const ghd = offer('ghd', [price('ghd-1', 100, 19000), price('ghd-2', 40, 17000), price('ghd-3', 10, 18500)]);
    expect(priceSeries([spd, ghd], checkedAt, 90, 7)).toEqual({
      start: at(90), end: at(0),
      lowest: [
        // In force as the period opened, so since the day it was recorded rather than the period's first.
        { from: at(90), to: at(40), price: 19000, listing: ghd, since: at(100) },
        // One step for as long as the lowest price stays the same, whatever the other store does meanwhile.
        { from: at(40), to: at(10), price: 17000, listing: ghd, since: at(40) },
        { from: at(10), to: at(0), price: 18000, listing: spd, since: at(10) },
      ],
      offers: [
        { listing: spd, today: 18000, steps: [{ from: at(60), to: at(20), price: 20000 }, { from: at(20), to: at(0), price: 18000 }] },
        { listing: ghd, today: 18500, steps: [{ from: at(90), to: at(40), price: 19000 }, { from: at(40), to: at(10), price: 17000 }, { from: at(10), to: at(0), price: 18500 }] },
      ],
    });
  });

  it('leaves a gap while nothing is in stock, and has no price today for an offer that is not on sale now', () => {
    const gone = offer('a', [price('a-1', 40, 20000), price('a-2', 30, 10000, { in_stock: false }), price('a-3', 10, 19000)]);
    const quiet = offer('quiet', [price('q-1', 35, 25000)], 20);
    const series = priceSeries([gone, quiet], checkedAt, 90, 7);
    expect(series.lowest.map(({ from, to, price: cents, listing }) => [from, to, cents, listing.id])).toEqual([
      [at(40), at(30), 20000, 'a'], [at(30), at(20), 25000, 'quiet'], [at(10), at(0), 19000, 'a'],
    ]);
    expect(series.offers.map(({ listing, today }) => [listing.id, today])).toEqual([['a', 19000], ['quiet', null]]);
  });

  it('has nothing for a period in which no offer was in stock, and leaves such offers out', () => {
    const never = offer('a', [price('a-1', 20, 20000, { in_stock: false })]);
    expect(priceSeries([never], checkedAt, 90, 7)).toEqual({ start: at(90), end: at(0), lowest: [], offers: [] });
  });

  it('holds a price first recorded this instant as a step of no length, so it can still be shown', () => {
    const fresh = offer('a', [price('a-1', 0, 15000)]);
    expect(priceSeries([fresh], checkedAt, 90, 7)).toEqual({
      start: at(90), end: at(0), lowest: [{ from: at(0), to: at(0), price: 15000, listing: fresh, since: at(0) }],
      offers: [{ listing: fresh, today: 15000, steps: [{ from: at(0), to: at(0), price: 15000 }] }],
    });
  });
});

describe('the lowest price steps, as the server works out its price ranges from them', () => {
  type Example = typeof examples.cases[number];
  const at = (days: number) => checkedAt.getTime() - days * DAY;
  const asOffers = ({ offers }: Example) => offers.map((seen, index) => offer(`${index}`,
    seen.prices.map((entry, number) => price(`${index}-${number}`, entry.days_ago, entry.item, { in_stock: (entry as { in_stock?: boolean }).in_stock ?? true })),
    seen.checked_days_ago));

  it.each(examples.cases.map(example => [example.name, example] as const))('%s', (_name, example) => {
    const series = priceSeries(asOffers(example), checkedAt, examples.days, examples.quiet_days);
    expect(series.lowest.map(({ from, to, price: cents }) => [from, to, cents]))
      .toEqual(example.lowest.map(([from, to, cents]) => [at(from), at(to), cents]));
    expect(series.offers.flatMap(({ today }) => today ?? []).sort((a, b) => a - b)).toEqual(example.today);
  });
});
