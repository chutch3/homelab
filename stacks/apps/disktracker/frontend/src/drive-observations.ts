import type { Offer, Observation } from './api';
import { compareObservations } from './price-change';

export type ObservationRow = { listing: Offer; observation: Observation };

export function combinedObservations(listings: Offer[]): ObservationRow[] {
  return listings
    .flatMap(listing => listing.observations.map(observation => ({ listing, observation })))
    .sort((a, b) => compareObservations(a.observation, b.observation));
}
