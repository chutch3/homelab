import type { Listing, Observation } from './api';
import { compareObservations } from './price-change';

export type ObservationRow = { listing: Listing; observation: Observation };

export function combinedObservations(listings: Listing[]): ObservationRow[] {
  return listings
    .flatMap(listing => listing.observations.map(observation => ({ listing, observation })))
    .sort((a, b) => compareObservations(a.observation, b.observation));
}
