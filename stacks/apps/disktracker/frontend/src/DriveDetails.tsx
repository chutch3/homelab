import { useEffect, useState, type ReactNode } from 'react';
import { Alert, Button, CloseButton, Drawer, Group, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import type { Condition, Drive, DriveDetail, Offer, DisktrackerApi, OfferSummary, Observation, PriceRow, RecordedPrice } from './api';
import { bestOffer } from './best-offer';
import { conditionChoices, priceLabel, startingCondition } from './drive-conditions';
import { DeleteOfferDialog } from './DeleteOfferDialog';
import { DeletePriceDialog } from './DeletePriceDialog';
import { Disclosure } from './Disclosure';
import { DriveForm } from './DriveForm';
import { MergeDriveForm } from './MergeDriveForm';
import { DriveObservationTable } from './DriveObservationTable';
import { DrivePriceChart } from './DrivePriceChart';
import { EntryForm } from './EntryForm';
import { sellerLabel, driveName } from './listing-display';
import { compareListings, type Period, type Sort } from './listing-query';
import { OfferForm } from './OfferForm';
import { OfferTable } from './OfferTable';
import { PriceCheck } from './PriceCheck';
import { SpecificationDetails } from './SpecificationDetails';

type Props = {
  api: DisktrackerApi; now: () => Date; nextId: () => string;
  /** The drive to show, by its key, and what to call it until it has loaded. */
  driveKey: string; title: string; sort: Sort;
  /** Counts the app's changes: the drive is loaded again after each. */
  revision: number;
  /** The condition to open on: that of the row the drive was opened from. */
  condition?: Condition;
  /** Whether the drive's data can be corrected here: specifications, offers and prices. */
  manage: boolean;
  /** Whether a table lies beside the panel's place: it then sits there, not over the page, in a window wide enough to keep every column. */
  besideTable: boolean;
  /** The days after which an unchecked offer no longer counts as on sale, and the days the price trend opens on. */
  recentDays: number; days: Period;
  onClose: () => void;
  onRecorded: (listingId: string) => Promise<void>;
  /** Reload after a change, replacing the page message when given one. */
  onChanged: (notice?: string, recorded?: RecordedPrice) => Promise<void>;
};

/** How many prices are asked for at once while a drive's are loaded. */
const PRICES_PER_REQUEST = 500;
const DAY = 86_400_000;
/** The drive a key names: drive:<id> for a drive, listing:<id> for an offer of none. */
export const driveIdOf = (key: string) => key.replace(/^(drive|listing):/, '');

/** One drive in a panel beside the list, a condition at a time: that condition's offers, price trend
 * and history, loaded when the drive is opened. Conditions are not mixed, as they are different
 * things to buy; each choice of condition says what it costs now, so they can still be compared. */
export function DriveDetails({ api, now, nextId, driveKey, title: named, sort, revision, condition: opensOn, manage, besideTable, recentDays, days, onClose, onRecorded, onChanged }: Props) {
  /** The drive's offers, each with its latest price, and its ranges; null until they have loaded. */
  const [summaries, setSummaries] = useState<OfferSummary[] | null>(null);
  const [ranges, setRanges] = useState<DriveDetail['ranges']>({});
  /** The period the price trend looks back over: chosen here, and what is asked for. */
  const [period, setPeriod] = useState<Period>(days);
  // null until the first answer, so a drive still loading is told apart from one with no prices.
  const [history, setHistory] = useState<Offer[] | null>(null);
  const [error, setError] = useState('');
  /** The offer whose price is being recorded in its row, by id. */
  const [checking, setChecking] = useState<string | null>(null);
  const [recording, setRecording] = useState<Offer | null>(null);
  const [editingDrive, setEditingDrive] = useState<Drive | null>(null);
  const [merging, setMerging] = useState<Drive | null>(null);
  const [editing, setEditing] = useState<Offer | null>(null);
  const [deletingOffer, setDeletingOffer] = useState<Offer | null>(null);
  const [deletingPrice, setDeletingPrice] = useState<{ listing: Offer; observation: Observation } | null>(null);
  // The drive, with its ranges over the period, and the prices of its offers in effect over it: asked
  // for by the drive, again when the period changes and after every change the app makes.
  useEffect(() => {
    const id = driveIdOf(driveKey);
    const since = new Date(now().getTime() - period * DAY).toISOString();
    let active = true;
    api.drive(id, period, recentDays).then(async found => {
      if (!active) return;
      setSummaries(found.offers); setRanges(found.ranges);
      const prices: PriceRow[] = [];
      for (let offset = 0; ; offset += PRICES_PER_REQUEST) {
        const page = await api.prices({ driveId: id, since, limit: PRICES_PER_REQUEST, offset });
        prices.push(...page.items);
        if (offset + PRICES_PER_REQUEST >= page.total) break;
      }
      if (!active) return;
      setHistory(found.offers.map(offer => ({ ...offer, observations: prices.filter(price => price.offer_id === offer.id)
        .map(({ offer_id: _offer, ...price }) => price) })));
      setError('');
    }).catch(err => {
      if (!active) return;
      // A drive whose last offer was just deleted is gone, and so is its panel.
      if (err instanceof Error && err.message === 'Drive not found') onClose();
      else setError(err instanceof Error ? err.message : 'Prices could not be loaded.');
    });
    return () => { active = false; };
  }, [api, driveKey, revision, period]);
  const choices = conditionChoices(summaries ?? []);
  const [chosen, setChosen] = useState<Condition | undefined>(opensOn);
  // The condition chosen can lose its last offer to a delete; the panel then falls back as it would on opening.
  const condition = choices.length ? startingCondition(choices, chosen) : opensOn;
  const stores = new Set((summaries ?? []).map(sellerLabel)).size;
  const offers = (history ?? []).filter(listing => listing.condition === condition).sort(compareListings(sort));
  const drive = summaries?.[0]?.drive ?? null;
  const lowest = bestOffer(offers);
  const title = summaries?.[0] ? driveName(summaries[0].drive) : named;
  const wide = useMediaQuery('(min-width: 1500px)', false, { getInitialValueInEffect: false }) && besideTable;
  /** The panel's frame: a region beside the table, which stays in reach, or a dialog over the page. */
  const frame = (body: ReactNode) => wide
    ? <aside aria-label={title} className="drive-aside"><div className="drive-aside-head"><h2>{title}</h2><CloseButton aria-label="Close" onClick={onClose} /></div>{body}</aside>
    : <Drawer opened onClose={onClose} title={title} position="right" size={760} closeButtonProps={{ 'aria-label': 'Close' }}>{body}</Drawer>;
  return <>
    {frame(<>
      {drive && <div className="drive-summary">
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">{drive.mpn}, {stores} store{stores === 1 ? '' : 's'}</Text>
          {manage && <Group gap="xs">
            <Button variant="default" onClick={() => setEditingDrive(drive)}>Edit specifications</Button>
            <Button variant="default" onClick={() => setMerging(drive)}>Merge another drive into this one</Button>
          </Group>}
        </Group>
      </div>}
      {/* One condition is nothing to choose between: it is named, not offered as a choice. */}
      {choices.length === 0 ? null : choices.length === 1 ? <p className="condition-only">{choices[0].label}</p> : <div role="radiogroup" aria-label="Condition" className="condition-switch segmented">
        {choices.map(choice => <label key={choice.condition} className="condition-choice">
          <input type="radio" name="condition" className="visually-hidden" checked={choice.condition === condition}
            onChange={() => { setChosen(choice.condition); setChecking(null); }} />
          <span className="condition-name">{choice.label}</span><span className="condition-price">{priceLabel(choice)}</span>
        </label>)}
      </div>}
      {error && <Alert color="red" role="alert" mb="md">{error}</Alert>}
      {history === null ? !error && <Text role="status" size="sm">Loading prices…</Text>
        : offers.length === 0 ? <Text size="sm" c="dimmed">No offers yet.</Text> : <>
          {/* Whether now is a good time to buy comes before where to buy it. */}
          <DrivePriceChart listings={offers} now={now()} quietDays={recentDays} days={period} onDays={setPeriod}
            range={ranges[condition as Condition] ?? null} />
          <OfferTable listings={offers} lowestId={lowest?.listing.id ?? null} now={now()} checking={checking} onCheck={setChecking}
            check={listing => <PriceCheck listing={listing} api={api} nextId={nextId} link={false}
              onRecorded={async (message, recorded) => { setChecking(null); await onChanged(message, recorded); }}
              more={<Button variant="subtle" onClick={() => { setChecking(null); setRecording(listing); }}>More options</Button>} />}
            onEdit={manage ? setEditing : undefined} onDelete={manage ? setDeletingOffer : undefined} />
          <Disclosure label="Price history" count={offers.reduce((sum, listing) => sum + listing.observations.length, 0)}>
            <DriveObservationTable listings={offers}
              onDelete={manage ? (listing, observation) => setDeletingPrice({ listing, observation }) : undefined} />
          </Disclosure>
        </>}
      {drive && <Disclosure label="Specifications">
        <SpecificationDetails value={drive.specifications} />
      </Disclosure>}
    </>)}
    {recording && <EntryForm api={api} now={now} nextId={nextId} listing={recording}
      onClose={() => setRecording(null)} onSaved={onRecorded} />}
    {editingDrive && <DriveForm drive={editingDrive} api={api} onClose={() => setEditingDrive(null)}
      onSaved={saved => onChanged(`Specifications saved for every offer of MPN ${saved.mpn}.`)}
      onAliasAdded={() => onChanged()} />}
    {merging && <MergeDriveForm drive={merging} api={api} nextId={nextId} onClose={() => setMerging(null)}
      onMerged={absorbed => onChanged(`Merged ${absorbed.mpn} into ${merging.mpn}.`)} />}
    {editing && <OfferForm listing={editing} api={api} onClose={() => setEditing(null)} onSaved={() => onChanged('Offer updated.')} />}
    {deletingPrice && <DeletePriceDialog {...deletingPrice} api={api} onClose={() => setDeletingPrice(null)}
      onDeleted={() => onChanged('Price deleted.')} />}
    {deletingOffer && <DeleteOfferDialog listing={deletingOffer} api={api} onClose={() => setDeletingOffer(null)}
      onDeleted={() => onChanged('Offer deleted.')} />}
  </>;
}
