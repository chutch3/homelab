import { useEffect, useState } from 'react';
import { Alert, Button, Drawer, Group, Text } from '@mantine/core';
import type { Condition, Drive, Listing, ListingsApi, ListingSummary, Observation } from './api';
import { bestOffer } from './best-offer';
import { conditionChoices, priceLabel, startingCondition } from './drive-conditions';
import { groupKeyFor } from './drive-groups';
import { DeleteOfferDialog } from './DeleteOfferDialog';
import { DeletePriceDialog } from './DeletePriceDialog';
import { Disclosure } from './Disclosure';
import { DriveForm } from './DriveForm';
import { DriveObservationTable } from './DriveObservationTable';
import { DrivePriceChart } from './DrivePriceChart';
import { EntryForm } from './EntryForm';
import { sellerLabel } from './listing-display';
import { compareListings, type Sort } from './listing-query';
import { OfferForm } from './OfferForm';
import { OfferTable } from './OfferTable';
import { PriceCheck } from './PriceCheck';
import { SpecificationDetails } from './SpecificationDetails';

type Props = {
  api: ListingsApi; now: () => Date; nextId: () => string;
  /** Every offer the app has loaded, and the drive (its group key) whose offers to show. */
  listings: ListingSummary[]; driveKey: string; sort: Sort; knownCapacities: Record<string, number>;
  /** The condition to open on: that of the row the drive was opened from. */
  condition?: Condition;
  /** Whether the drive's data can be corrected here: specifications, offers and prices. */
  manage: boolean;
  onClose: () => void;
  onRecorded: (listingId: string, observedAt: string) => Promise<void>;
  /** Reload after a change, replacing the page message when given one. */
  onChanged: (notice?: string) => Promise<void>;
};

/** One drive in a panel beside the list, a condition at a time: that condition's offers, price trend
 * and history, loaded when the drive is opened. Conditions are not mixed, as they are different
 * things to buy; each choice of condition says what it costs now, so they can still be compared. */
export function DriveDetails({ api, now, nextId, listings, driveKey, sort, knownCapacities, condition: opensOn, manage, onClose, onRecorded, onChanged }: Props) {
  // null until the first answer, so a drive still loading is told apart from one with no prices.
  const [history, setHistory] = useState<Listing[] | null>(null);
  const [error, setError] = useState('');
  /** The offer whose price is being recorded in its row, by id. */
  const [checking, setChecking] = useState<string | null>(null);
  const [recording, setRecording] = useState<Listing | null>(null);
  const [editingDrive, setEditingDrive] = useState<Drive | null>(null);
  const [editing, setEditing] = useState<Listing | null>(null);
  const [deletingOffer, setDeletingOffer] = useState<Listing | null>(null);
  const [deletingPrice, setDeletingPrice] = useState<{ listing: Listing; observation: Observation } | null>(null);
  const summaries = listings.filter(listing => groupKeyFor(listing) === driveKey);
  // The app reloads its offers after every change, which loads this drive's history again.
  useEffect(() => {
    const ids = listings.filter(listing => groupKeyFor(listing) === driveKey).map(listing => listing.id);
    let active = true;
    api.priceHistory(ids).then(found => { if (active) { setHistory(found); setError(''); } })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Prices could not be loaded.'); });
    return () => { active = false; };
  }, [api, listings, driveKey]);
  const choices = conditionChoices(summaries);
  const [chosen, setChosen] = useState(() => startingCondition(choices, opensOn));
  // The condition chosen can lose its last offer to a delete; the panel then falls back as it would on opening.
  const condition = startingCondition(choices, chosen);
  const stores = new Set(summaries.map(sellerLabel)).size;
  const offers = (history ?? []).filter(listing => listing.condition === condition && summaries.some(summary => summary.id === listing.id)).sort(compareListings(sort));
  const drive = summaries[0].drive;
  const lowest = bestOffer(offers);
  return <>
    <Drawer opened onClose={onClose} title={summaries[0].title} position="right" size={760} closeButtonProps={{ 'aria-label': 'Close' }}>
      {drive && <div className="drive-summary">
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">MPN {drive.mpn} · {stores} store{stores === 1 ? '' : 's'} · {summaries.length} offer{summaries.length === 1 ? '' : 's'}</Text>
          {manage && <Button variant="default" onClick={() => setEditingDrive(drive)}>Edit specifications</Button>}
        </Group>
      </div>}
      <div role="radiogroup" aria-label="Condition" className="condition-switch">
        {choices.map(choice => <label key={choice.condition} className="condition-choice">
          <input type="radio" name="condition" className="visually-hidden" checked={choice.condition === condition}
            onChange={() => { setChosen(choice.condition); setChecking(null); }} />
          <span className="condition-name">{choice.label}</span><span className="condition-price">{priceLabel(choice)}</span>
        </label>)}
      </div>
      {error && <Alert color="red" role="alert" mb="md">{error}</Alert>}
      {history === null ? !error && <Text role="status" size="sm">Loading prices…</Text>
        : offers.length === 0 ? <Text size="sm" c="dimmed">No offers yet.</Text> : <>
          <OfferTable listings={offers} lowestId={lowest?.listing.id ?? null} checking={checking} onCheck={setChecking}
            check={listing => <PriceCheck listing={listing} api={api} nextId={nextId} link={false}
              onRecorded={async message => { setChecking(null); await onChanged(message); }}
              more={<Button variant="subtle" onClick={() => { setChecking(null); setRecording(listing); }}>More options</Button>} />}
            onEdit={manage ? setEditing : undefined} onDelete={manage ? setDeletingOffer : undefined} />
          <DrivePriceChart listings={offers} />
          <Disclosure label="Price history" count={offers.reduce((sum, listing) => sum + listing.observations.length, 0)}>
            <DriveObservationTable listings={offers}
              onDelete={manage ? (listing, observation) => setDeletingPrice({ listing, observation }) : undefined} />
          </Disclosure>
        </>}
      {drive && <Disclosure label="Specifications">
        <SpecificationDetails value={drive.specifications} />
      </Disclosure>}
    </Drawer>
    {recording && <EntryForm knownCapacities={knownCapacities} api={api} now={now} nextId={nextId} listing={recording}
      onClose={() => setRecording(null)} onSaved={onRecorded} />}
    {editingDrive && <DriveForm drive={editingDrive} api={api} onClose={() => setEditingDrive(null)}
      onSaved={saved => onChanged(`Specifications saved for every offer of MPN ${saved.mpn}.`)}
      onAliasAdded={() => onChanged()} />}
    {editing && <OfferForm listing={editing} api={api} onClose={() => setEditing(null)} onSaved={() => onChanged('Offer updated.')} />}
    {deletingPrice && <DeletePriceDialog {...deletingPrice} api={api} onClose={() => setDeletingPrice(null)}
      onDeleted={() => onChanged('Price deleted.')} />}
    {deletingOffer && <DeleteOfferDialog listing={deletingOffer} api={api} onClose={() => setDeletingOffer(null)}
      onDeleted={() => onChanged('Offer deleted.')} />}
  </>;
}
