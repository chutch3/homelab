import type { Offer } from './api';

export type BestOffer = { listing: Offer; price: number };

/** The cheapest offer in stock, of those not doubted: one that may not be one drive of its
 * capacity is never called the best. */
export function bestOffer(listings: Offer[]): BestOffer | null {
  let best: BestOffer | null = null;
  for (const listing of listings.filter(listing => listing.latest.in_stock && !listing.doubt)) {
    const price = listing.latest.total_cents;
    if (best === null || price < best.price) best = { listing, price };
  }
  return best;
}
