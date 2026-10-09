import type { Listing, Observation } from './api';

export type LowestObserved = { listing: Listing; observation: Observation; count: number; from: string; to: string };

/** The cheapest total recorded while in stock, over every in-stock price shown; a sold-out price was not purchasable. */
export function lowestObserved(listings: Listing[]): LowestObserved | null {
  const prices = listings
    .flatMap(listing => listing.observations.filter(observation => observation.in_stock).map(observation => ({ listing, observation })))
    .sort((a, b) => a.observation.observed_at.localeCompare(b.observation.observed_at));
  if (!prices.length) return null;
  const lowest = prices.reduce((best, price) => price.observation.total_cents <= best.observation.total_cents ? price : best);
  return {
    ...lowest, count: prices.length,
    from: prices[0].observation.observed_at, to: prices[prices.length - 1].observation.observed_at,
  };
}
