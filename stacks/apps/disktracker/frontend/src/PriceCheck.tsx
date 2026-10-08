import { useState, type ReactNode } from 'react';
import { Button, Text, TextInput } from '@mantine/core';
import type { ListingsApi, ListingSummary, PriceInput } from './api';
import { dollars } from './listing-display';
import { parseDollars } from './money';

type Props = {
  listing: ListingSummary; api: ListingsApi; nextId: () => string;
  /** Told what was recorded, in a sentence, once it is saved. */
  onRecorded: (message: string) => Promise<void>;
  /** Whether to link to the store's page; left out where the row it sits under already does. */
  link?: boolean;
  /** Shown after the answers: a way to the full form, where there is one. */
  more?: ReactNode;
};
type Answer = 'same' | 'new' | 'out';

/** What an offer's store page says now, recorded in one step: no change, a new price, or out of
 * stock. Shipping stays as last recorded. Nothing else can be answered while one is being saved. */
export function PriceCheck({ listing, api, nextId, onRecorded, link = true, more }: Props) {
  const [price, setPrice] = useState('');
  const [saving, setSaving] = useState<Answer | null>(null);
  const [error, setError] = useState('');
  const record = async (answer: Answer, change: Pick<PriceInput, 'item_price_cents' | 'in_stock'>, message: string) => {
    setError(''); setSaving(answer);
    try {
      await api.recordPrice({
        mpn: listing.mpn ?? '', store: listing.store, seller: listing.seller, condition: listing.condition,
        title: listing.title, url: listing.url, capacity_gb: null,
        shipping_cents: listing.latest.shipping_cents ?? 0, observed_at: null, notes: '', ...change,
      }, nextId());
      setPrice('');
      await onRecorded(message);
    } catch (err) { setError(err instanceof Error ? err.message : 'The price could not be saved.'); }
    finally { setSaving(null); }
  };
  const recordNew = () => {
    let item: number | null;
    try { item = parseDollars(price); } catch (err) { setError((err as Error).message); return; }
    if (item === null) setError('Enter the new price.');
    else if (item === 0) setError('Enter a price above zero.');
    else void record('new', { item_price_cents: item, in_stock: true }, `Recorded ${dollars(item)} for ${listing.title}.`);
  };
  const busy = saving !== null;
  const { latest } = listing;
  return <div className="price-check">
    <div className="price-check-answers">
      {link && listing.url && <a className="seller-link" href={listing.url} target="_blank" rel="noopener noreferrer">Open store page ↗</a>}
      <Button variant="default" disabled={busy} loading={saving === 'same'}
        onClick={() => record('same', { item_price_cents: latest.item_price_cents, in_stock: latest.in_stock }, `Checked ${listing.title}: no change.`)}>No change</Button>
      <span className="price-check-new">
        <TextInput w={130} placeholder="New price" inputMode="decimal" aria-label={`New price for ${listing.title}`} disabled={busy}
          value={price} onChange={event => { setPrice(event.currentTarget.value); setError(''); }}
          onKeyDown={event => { if (event.key === 'Enter') recordNew(); }} />
        <Button disabled={busy} loading={saving === 'new'} onClick={recordNew}>Save</Button>
      </span>
      <Button variant="default" disabled={busy} loading={saving === 'out'}
        onClick={() => record('out', { item_price_cents: null, in_stock: false }, `Marked ${listing.title} out of stock.`)}>Out of stock</Button>
      {more}
    </div>
    {error && <Text size="sm" role="alert" className="field-error">{error}</Text>}
  </div>;
}
