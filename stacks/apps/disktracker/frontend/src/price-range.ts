import type { Offer } from './api';
import { compareObservations } from './price-change';

const DAY = 86_400_000;

/** A price holding from one moment to another, in cents and milliseconds. */
export type PriceStep = { from: number; to: number; price: number };
/** A step of the lowest price at any store: the offer that had it, and since when that price was
 * the lowest (earlier than the step's start when it already was as the period opened). */
export type LowestStep = PriceStep & { listing: Offer; since: number };
/** A drive's item price over a period: the lowest at any store, step by step with gaps where none
 * had it in stock, and each offer's own steps with what it costs today (null when not on sale now). */
export type PriceSeries = {
  start: number; end: number; lowest: LowestStep[];
  offers: { listing: Offer; today: number | null; steps: PriceStep[] }[];
};

/** The stretches of time an offer could be bought at a price: each price holds until the next one
 * recorded, an out-of-stock record ends it, and an offer unchecked for longer than quietDays is
 * taken to have ended at its last check rather than still to be on sale. The stretch still open
 * now, if there is one, is what the offer costs today. */
function stretches(listing: Offer, now: number, quietDays: number): (PriceStep & { open: boolean })[] {
  const checked = Date.parse(listing.last_checked_at);
  const end = now - checked > quietDays * DAY ? checked : now;
  const prices = [...listing.observations].sort(compareObservations);
  return prices.flatMap((price, index) => {
    const from = Date.parse(price.observed_at);
    const to = Math.min(end, index + 1 < prices.length ? Date.parse(prices[index + 1].observed_at) : end);
    return price.in_stock && to >= from ? [{ from, to, price: price.item_price_cents, open: index + 1 === prices.length && end === now }] : [];
  });
}

/** The item prices of these offers over the days up to now, for drawing: the server works out a
 * drive's range from the same lowest steps, and shared examples hold the two to one answer. The offers are one drive's in one
 * condition; shipping is left out, as it is from every price history. A price held for no time
 * counts only when it is today's: one recorded this instant, which ends the lowest as a step of no length. */
export function priceSeries(listings: Offer[], now: Date, days: number, quietDays: number): PriceSeries {
  const end = now.getTime(), start = end - days * DAY;
  const held = listings.flatMap(listing => stretches(listing, end, quietDays)
    .map(stretch => ({ ...stretch, from: Math.max(stretch.from, start), since: stretch.from, listing }))
    .filter(stretch => stretch.to > stretch.from || stretch.open));
  const cheapest = (on: (stretch: typeof held[number]) => boolean) => held.filter(on).sort((a, b) => a.price - b.price)[0];
  // Between one change and the next, the lowest price is whichever offer then on sale is cheapest.
  const moments = [...new Set(held.flatMap(stretch => [stretch.from, stretch.to]))].sort((a, b) => a - b);
  const lowest: LowestStep[] = [];
  moments.slice(0, -1).forEach((moment, index) => {
    const winner = cheapest(stretch => stretch.from <= moment && stretch.to > moment), last = lowest[lowest.length - 1];
    if (!winner) return;
    if (last && last.to === moment && last.price === winner.price) last.to = moments[index + 1];
    else lowest.push({ from: moment, to: moments[index + 1], price: winner.price, listing: winner.listing, since: moment === start ? winner.since : moment });
  });
  // The lowest ends on today's price: where the last step is not it (a price changed this instant), a step of no length is.
  const current = cheapest(stretch => stretch.open), last = lowest[lowest.length - 1];
  if (current && (last?.to !== end || last.price !== current.price)) lowest.push({ from: end, to: end, price: current.price, listing: current.listing, since: end });
  return {
    start, end, lowest,
    offers: listings.flatMap(listing => {
      const own = held.filter(stretch => stretch.listing === listing);
      return own.length ? [{ listing, steps: own.map(({ from, to, price }) => ({ from, to, price })), today: own.find(stretch => stretch.open)?.price ?? null }] : [];
    }),
  };
}
