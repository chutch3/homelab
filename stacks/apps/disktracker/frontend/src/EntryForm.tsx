import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Autocomplete, Button, Group, Modal, NativeSelect, SegmentedControl, Stack, Text, TextInput, Textarea } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useForm } from '@mantine/form';
import { ApiValidationError, type CatalogDrive, type Condition, type Drive, type Offer, type DisktrackerApi, type ObservationInput, type Store } from './api';
import { CapacityField } from './CapacityField';
import { parseDollars } from './money';
import { formFieldErrors, validateEntry, type EntryDefaults, type EntryValues } from './entry-validation';
import { asksForSeller, capacityLabel, conditions, conditionLabel, dollars, sellerLabel } from './listing-display';

/** Whether a drive goes by this MPN, as its own or another of its MPNs, in any case. */
const goesBy = (drive: Drive, mpn: string) => [drive.mpn, ...drive.aliases].some(name => name.toUpperCase() === mpn.toUpperCase());
/** The drives the server finds by an MPN typed, and the one recorded under it, if any is. */
type Found = { mpn: string; drives: CatalogDrive[] };
const recordedUnder = ({ mpn, drives }: Found) => drives.find(row => goesBy(row.drive, mpn))?.drive;

const localTime = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 19);
type EntryProps = {
  api: DisktrackerApi; now: () => Date; nextId: () => string; listing: Offer | null;
  /** The stores a new offer can be recorded under. */
  stores?: Store[];
  /** Where a new offer starts, and a hook to remember the store and condition a new offer used. */
  defaults?: EntryDefaults; onEntered?: (defaults: EntryDefaults) => void;
  /** Offered for a new offer: after saving, start another instead of closing. */
  onAnother?: (savedTitle: string) => void;
  /** The title of the price just saved, when this form follows it. */
  previous?: string;
  onClose: () => void; onSaved: (listingId: string) => Promise<void>;
};

export function EntryForm({ listing, stores = [], defaults = { store: '', condition: '' }, onEntered, onAnother, previous, api, now, nextId, onClose, onSaved }: EntryProps) {
  const priceOnly = listing !== null;
  const [requestId] = useState(nextId);
  const [changingDate, setChangingDate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const formElement = useRef<HTMLFormElement>(null);
  const another = useRef(false);
  const focusFirstError = (errors: Record<string, unknown>) => {
    for (const input of formElement.current?.querySelectorAll<HTMLElement>('[data-path]') ?? []) {
      if (errors[input.dataset.path!]) {
        const details = input.closest('details');
        if (details) details.open = true;
        input.focus(); break;
      }
    }
  };
  const form = useForm<EntryValues>({
    validate: values => validateEntry(values, priceOnly, knownCapacity.current !== undefined),
    validateInputOnBlur: true,
    clearInputErrorOnChange: false,
    initialValues: {
      title: '', mpn: '', store: defaults.store, seller: '', url: '', capacity: '', condition: defaults.condition,
      item: '', shipping: '', inStock: true, observed: localTime(now()), notes: '',
    },
  });
  // Drives already recorded, found by the MPN as it is typed, once it stops changing.
  const lookUp = useCallback((mpn: string) =>
    api.catalogDrives({ q: mpn, limit: 8, offset: 0 }).then(page => ({ mpn, drives: page.items })), [api]);
  const [found, setFound] = useState<Found | null>(null);
  const typedMpn = form.values.mpn.trim();
  const [settledMpn] = useDebouncedValue(typedMpn, 250);
  useEffect(() => {
    if (priceOnly || !settledMpn) return;
    let current = true;
    // Without an answer the form still works: it asks for the capacity, and the server checks it.
    lookUp(settledMpn).then(answer => { if (current) setFound(answer); }).catch(() => {});
    return () => { current = false; };
  }, [lookUp, settledMpn, priceOnly]);
  /** The capacity of the drive recorded under the MPN as it is now, once the server has said. */
  const recorded = found && found.mpn.toUpperCase() === typedMpn.toUpperCase() ? recordedUnder(found) : undefined;
  const knownCapacity = useRef<number | undefined>(undefined);
  knownCapacity.current = recorded?.capacity_gb;
  const seller = asksForSeller(form.values.store);
  const [pasted, setPasted] = useState('');
  const [fills, setFills] = useState(0);
  /** What the last pasted text gave and did not give, by field name as the form calls it. */
  const [filled, setFilled] = useState<{ found: string[]; missing: string[] } | null>(null);
  /** The field to move to once a fill has been drawn: the first one left for a person. */
  const focusAfterFill = useRef<string | null>(null);
  useEffect(() => {
    const path = focusAfterFill.current;
    focusAfterFill.current = null;
    if (path) formElement.current?.querySelector<HTMLElement>(`[data-path="${path}"]`)?.focus();
  }, [fills]);
  // Fills the form from text copied off a store page; a person still checks it and saves.
  const fillIn = async () => {
    setError('');
    try {
      const facts = await api.readListing(pasted);
      form.setValues({
        ...(facts.title && { title: facts.title }), ...(facts.mpn && { mpn: facts.mpn }),
        ...(facts.capacity_gb && { capacity: String(facts.capacity_gb) }), ...(facts.condition && { condition: facts.condition }),
        ...(facts.item_price_cents !== null && { item: (facts.item_price_cents / 100).toFixed(2) }),
      });
      // A drive already recorded brings its own capacity, so none is asked of the text.
      const named = facts.mpn?.trim() ? await lookUp(facts.mpn.trim()) : null;
      if (named) setFound(named);
      const capacityKnown = Boolean(facts.capacity_gb) || Boolean(named && recordedUnder(named));
      const read: [name: string, path: string | null, found: boolean][] = [
        ['title', null, Boolean(facts.title)], ['MPN', 'mpn', Boolean(facts.mpn)], ['capacity', 'capacity', capacityKnown],
        ['condition', 'condition', Boolean(facts.condition)], ['price', 'item', facts.item_price_cents !== null],
      ];
      setFilled({ found: read.filter(([, , found]) => found).map(([name]) => name), missing: read.filter(([, , found]) => !found).map(([name]) => name) });
      focusAfterFill.current = read.find(([, path, found]) => path && !found)?.[1] ?? null;
      setFills(count => count + 1);
    } catch (err) { setError(err instanceof Error ? err.message : 'The text could not be read.'); }
  };
  const submit = form.onSubmit(async values => {
    setError(''); setSaving(true);
    try {
      const observation: ObservationInput = {
        item_price_cents: parseDollars(values.item), shipping_cents: parseDollars(values.shipping) ?? 0, in_stock: values.inStock,
        observed_at: changingDate ? new Date(values.observed).toISOString() : null, notes: values.notes.trim(),
      };
      const offer = listing
        ? { mpn: listing.mpn ?? '', store: listing.store, seller: listing.seller, condition: listing.condition, title: listing.title,
          url: listing.url, capacity_gb: null }
        : { mpn: values.mpn.trim(), store: values.store, seller: seller ? values.seller.trim() : '', condition: values.condition as Condition,
          title: values.title.trim() || null, url: values.url.trim() || null, capacity_gb: knownCapacity.current ? null : Number(values.capacity.trim()) };
      const saved = await api.recordPrice({ ...offer, ...observation }, requestId);
      if (!listing) onEntered?.({ store: values.store, condition: values.condition });
      // A price entered by hand is recorded or refused: it is never queued or ignored.
      await onSaved(saved.offer_id ?? '');
      if (another.current && onAnother) onAnother(offer.title || offer.mpn); else onClose();
    } catch (err) {
      if (err instanceof ApiValidationError) {
        const errors = formFieldErrors(err.fields, priceOnly);
        form.setErrors(errors);
        focusFirstError(errors);
        if (!Object.keys(errors).length || Object.keys(errors).length < Object.keys(err.fields).length) {
          setError(err.message);
        }
      } else {
        setError(err instanceof Error ? err.message : 'The entry could not be saved.');
      }
    }
    finally { setSaving(false); }
  }, focusFirstError);
  return <Modal opened onClose={() => { if (!saving) onClose(); }} title="Record price" size="lg" centered>
    <form ref={formElement} onSubmit={submit} noValidate>
      <Stack gap="md">
        {previous && <Text role="status" size="sm" c="dimmed">Saved {previous}. Add the next offer.</Text>}
        {!listing && <div className="entry-paste">
          <Textarea label="Paste from store page" aria-label="Paste from store page" autosize minRows={2} maxRows={6}
            description="Copy the title and price from the store's page; Fill in reads what it can"
            value={pasted} onChange={event => setPasted(event.currentTarget.value)} />
          <Group gap="sm"><Button variant="default" onClick={fillIn} disabled={!pasted.trim()}>Fill in</Button>
            {filled && <Text role="status" size="sm">{filled.found.length ? `Filled in: ${filled.found.join(', ')}.` : 'Nothing could be read from that text.'}
              {filled.missing.length > 0 && ` Not found: ${filled.missing.join(', ')}.`}</Text>}</Group>
        </div>}
        {listing ? <Text size="sm">{listing.title} · {sellerLabel(listing)} · {conditionLabel(listing.condition)}</Text> : <>
          <div className="entry-grid">
            <NativeSelect label="Store" aria-label="Store" required data={[{ value: '', label: 'Choose store' }, ...stores.map(store => ({ value: store.key, label: store.name }))]} {...form.getInputProps('store')} />
            {seller && <TextInput label="Seller name" aria-label="Seller name" maxLength={120} required
              placeholder="Store name" {...form.getInputProps('seller')} />}
            {/* Beside the store, or on its own line when the store needs naming. */}
            <TextInput label="Store page URL" aria-label="Store page URL" type="url" placeholder="https://" className={seller ? 'entry-wide' : undefined}
              {...form.getInputProps('url')} />
          </div>
          <div className="entry-grid">
            <Autocomplete label="MPN" aria-label="MPN" required maxLength={100} placeholder="e.g. ST18000NM000J" limit={8}
              data={(found?.drives ?? []).map(row => row.drive.mpn)} {...form.getInputProps('mpn')}
              // The server has found them by any name they go by: each is shown as it was found.
              filter={({ options }) => options}
              renderOption={({ option }) => `${option.value} · ${found?.drives.find(row => row.drive.mpn === option.value)?.title ?? ''}`} />
            {recorded ? <Text size="sm" className="entry-known">{capacityLabel(recorded.capacity_gb)}, as recorded for this drive</Text>
              : <CapacityField key={fills} value={form.values.capacity} error={form.errors.capacity}
                onChange={capacity => form.setFieldValue('capacity', capacity)} />}
          </div>
        </>}
        {listing && <Text size="sm" c="dimmed">Previous item price: {dollars(listing.latest.item_price_cents)}. Enter what you checked this time.</Text>}
        <div className={listing ? 'entry-grid' : 'entry-grid entry-price'}>
          {!listing && <NativeSelect label="Condition" aria-label="Condition" required data={[{ value: '', label: 'Choose condition' }, ...conditions]} {...form.getInputProps('condition')} />}
          <TextInput label="Item price (USD)" aria-label="Item price (USD)" inputMode="decimal" required {...form.getInputProps('item')} />
          <TextInput label="Shipping & fees (USD)" aria-label="Shipping & fees (USD)" inputMode="decimal" placeholder="Free" {...form.getInputProps('shipping')} />
        </div>
        <SegmentedControl aria-label="Stock" className="entry-stock" data={[{ value: 'in', label: 'In stock' }, { value: 'out', label: 'Out of stock' }]}
          value={form.values.inStock ? 'in' : 'out'} onChange={value => form.setFieldValue('inStock', value === 'in')} />
        <details className="entry-more">
          <summary>More details</summary>
          <Stack gap="md" mt="sm">
            {!listing && <TextInput label="Offer title" aria-label="Offer title" maxLength={160} placeholder="Defaults to the MPN" {...form.getInputProps('title')} />}
            {changingDate
              ? <TextInput label="Checked at (local time)" aria-label="Checked at (local time)" type="datetime-local" step="1" required {...form.getInputProps('observed')} />
              : <Group gap="xs"><Text size="sm" c="dimmed">Checked now.</Text>
                <Button variant="subtle" onClick={() => setChangingDate(true)}>Change date</Button></Group>}
            <Textarea label="Notes" aria-label="Notes" maxLength={2000} {...form.getInputProps('notes')} />
          </Stack>
        </details>
        {error && <Alert color="red" role="alert">{error}</Alert>}
        <Group justify="flex-end"><Button variant="default" onClick={onClose} disabled={saving}>Cancel</Button>{!listing && onAnother && <Button type="submit" variant="default" disabled={saving}
          onClick={() => { another.current = true; }}>Save and add another</Button>}
          <Button type="submit" loading={saving} onClick={() => { another.current = false; }}>Save price</Button></Group>
      </Stack>
    </form>
  </Modal>;
}
