import type { Listing } from './api';

export type BestOffer = { listing: Listing; price: number };

export function bestOffer(listings: Listing[]): BestOffer | null {
  let best: BestOffer | null = null;
  for (const listing of listings.filter(listing => listing.latest.in_stock)) {
    const price = listing.latest.total_cents;
    if (best === null || price < best.price) best = { listing, price };
  }
  return best;
}
