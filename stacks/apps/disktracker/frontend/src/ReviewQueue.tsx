import { useEffect, useState } from 'react';
import { Alert, Autocomplete, Button, Group, Modal, NativeSelect, Radio, Stack, Table, Text } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useForm } from '@mantine/form';
import type { Condition, DisktrackerApi, Drive, Page, ReviewFilter, ReviewItem, ReviewReason, Store } from './api';
import { CapacityField } from './CapacityField';
import { capacityLabel, conditions, dollars } from './listing-display';
import { Pager } from './Pager';
import { usePageSize } from './paging';

const reasons: Record<ReviewReason, string> = {
  missing_mpn: 'No MPN',
  missing_condition: 'Unknown condition',
  capacity_conflict: 'Capacity mismatch',
  missing_capacity: 'Needs capacity',
  missing_price: 'No price yet',
  not_a_single_drive: 'Not one drive',
  implausible_capacity: 'Capacity too large',
};

type Asked = { page: number; filter: ReviewFilter; attempt: number };

/** The page of the review queue asked for, as the API last answered it. Only the answer to what
 * was asked last is shown: one that comes after it, asked before, is dropped. A page left empty by
 * its offers being dealt with gives way to the last page there is, worked out from the total.
 * Asked again whenever `revision` changes. */
export function useReviewQueue(api: DisktrackerApi, storage: Pick<Storage, 'getItem' | 'setItem'>, revision: number) {
  const [size, keepSize] = usePageSize(storage, 'review-queue');
  const [asked, setAsked] = useState<Asked>({ page: 0, filter: {}, attempt: 0 });
  /** The last answer, with the page it is. */
  const [shown, setShown] = useState<{ page: number; found: Page<ReviewItem> } | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let current = true;
    api.reviewItems({ limit: size, offset: asked.page * size, ...asked.filter }).then(found => {
      if (!current) return;
      const last = Math.max(0, Math.ceil(found.total / size) - 1);
      if (!found.items.length && last < asked.page) { setAsked({ ...asked, page: last }); return; }
      setShown({ page: asked.page, found }); setError('');
    }).catch(err => { if (current) setError(err instanceof Error ? err.message : 'Unknown error.'); });
    return () => { current = false; };
  }, [api, size, asked, revision]);
  return {
    items: shown?.found.items ?? [], total: shown?.found.total ?? 0, loaded: shown !== null, error,
    page: shown?.page ?? 0, size, filter: asked.filter,
    setPage: (page: number) => setAsked({ ...asked, page }),
    setFilter: (filter: ReviewFilter) => setAsked({ ...asked, page: 0, filter }),
    setSize: (next: number) => { keepSize(next); setAsked({ ...asked, page: 0 }); },
    retry: () => setAsked({ ...asked, attempt: asked.attempt + 1 }),
  };
}

type Props = {
  api: DisktrackerApi; storage: Pick<Storage, 'getItem' | 'setItem'>;
  /** The stores, to name the one each offer was read from. */
  stores: Store[];
  /** Every offer waiting, however the queue is narrowed. */
  all: number;
  /** Counts changes made anywhere: the queue is asked for again after each. */
  revision: number;
  onChanged: () => Promise<void>;
};

/** Offers a collector read but could not place: each is resolved by naming its drive, or ignored. */
export function ReviewQueue({ api, storage, stores, all, revision, onChanged }: Props) {
  const { items, total, loaded, error: loadError, page, size: pageSize, filter, setPage: onPage, setSize: onPageSize, setFilter: onFilter, retry } = useReviewQueue(api, storage, revision);
  const [resolving, setResolving] = useState<ReviewItem | null>(null);
  /** The offer being asked about before it is ignored, by id: ignoring is not undone from here. */
  const [confirming, setConfirming] = useState<string | null>(null);
  const [ignoring, setIgnoring] = useState(false);
  const [error, setError] = useState('');
  const narrowed = filter.store !== undefined || filter.reason !== undefined;
  const ignore = async (item: ReviewItem) => {
    setError(''); setIgnoring(true);
    try { await api.decide(item.id, { decision: 'ignore' }); setConfirming(null); await onChanged(); }
    catch (err) { setError(err instanceof Error ? err.message : 'The offer could not be ignored.'); }
    finally { setIgnoring(false); }
  };
  /** The offer after this one on the page, to resolve next. */
  const after = (item: ReviewItem) => items[items.findIndex(other => other.id === item.id) + 1] ?? null;
  return <section id="review-queue" aria-labelledby="review-queue-heading" className="admin-section panel">
    <h2 id="review-queue-heading">Needs matching{all > 0 && <span className="count"> ({narrowed ? `${total} of ${all}` : total})</span>}</h2>
    <Stack gap="sm">
      {all > 0 && <Text size="sm" c="dimmed" className="section-note">Offers the collector couldn’t match to a drive.</Text>}
      {all > 0 && <Group gap="sm" className="review-filters">
        <NativeSelect label="Why" aria-label="Why" value={filter.reason ?? ''}
          data={[{ value: '', label: 'Any reason' }, ...Object.entries(reasons).map(([value, label]) => ({ value, label }))]}
          onChange={event => onFilter({ ...filter, reason: (event.currentTarget.value || undefined) as ReviewReason | undefined })} />
        <NativeSelect label="Store" aria-label="Store" value={filter.store ?? ''}
          data={[{ value: '', label: 'Any store' }, ...stores.map(store => ({ value: store.key, label: store.name }))]}
          onChange={event => onFilter({ ...filter, store: event.currentTarget.value || undefined })} />
      </Group>}
      {error && <Alert color="red" role="alert">{error}</Alert>}
      {loadError ? <Alert color="red" role="alert"><Text size="sm" mb="sm">The offers to match could not be loaded: {loadError}</Text>
        <Button variant="default" onClick={retry}>Try again</Button></Alert>
      : !loaded ? <Text size="sm" c="dimmed" role="status" aria-label="Loading offers to match">Loading…</Text>
      : items.length === 0 ? <Text size="sm" className="all-clear">{narrowed ? 'Nothing to match here.' : 'Nothing to match.'}</Text> : <Table aria-label="Offers to match" className="todo-list">
        <Table.Thead><Table.Tr><Table.Th>Offer</Table.Th><Table.Th>Why</Table.Th><Table.Th className="numeric">Price</Table.Th>
          <Table.Th>Store</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{items.map(item => <Table.Tr key={item.id}>
          <Table.Td className="todo-title"><a className="offer-link" href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a></Table.Td>
          <Table.Td data-label="Why">{reasons[item.reason]}</Table.Td>
          <Table.Td data-label="Price" className="mono">{item.item_price_cents === null ? '—' : dollars(item.item_price_cents)}</Table.Td>
          <Table.Td data-label="Store">{stores.find(store => store.key === item.store)?.name ?? item.store}</Table.Td>
          <Table.Td className="todo-actions">{confirming === item.id
            ? <Group gap="sm" wrap="nowrap"><Text size="sm">Ignore this offer? Later collections skip its page too.</Text>
              <Button color="red" loading={ignoring} onClick={() => ignore(item)}>Yes, ignore</Button>
              <Button variant="default" disabled={ignoring} onClick={() => setConfirming(null)}>Keep</Button></Group>
            : <Group gap="md" wrap="nowrap">
              <Button onClick={() => setResolving(item)}>Resolve</Button>
              <Button variant="subtle" onClick={() => setConfirming(item.id)}>Ignore</Button></Group>}</Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table>}
      <Pager label="Needs matching" page={page} total={total} pageSize={pageSize} onPage={onPage} onPageSize={onPageSize} />
    </Stack>
    {resolving && <ResolveForm key={resolving.id} item={resolving} next={after(resolving)} api={api}
      onClose={() => setResolving(null)} onNext={setResolving} onResolved={onChanged} />}
  </section>;
}

/** What an offer waits for, said of this offer. */
function why(item: ReviewItem, drive: Drive | null): string {
  const said = item.capacity_gb === null ? null : capacityLabel(item.capacity_gb);
  switch (item.reason) {
    case 'missing_mpn': return 'The store names no MPN.';
    case 'missing_condition': return 'The store does not say what condition it is in.';
    case 'missing_capacity': return 'The store gives no capacity, and no drive is recorded for its MPN.';
    case 'missing_price': return 'The store gives no price for it yet.';
    case 'not_a_single_drive': return 'Its title reads as several drives, tape or other equipment.';
    case 'implausible_capacity': return `The store says ${said ?? 'no capacity'}: more than any drive holds.`;
    case 'capacity_conflict': return drive && said
      ? `The store says ${said}; ${drive.mpn} is recorded as ${capacityLabel(drive.capacity_gb)}.`
      : 'Its capacity differs from the drive its MPN names.';
  }
}

type ResolveProps = {
  item: ReviewItem; next: ReviewItem | null; api: DisktrackerApi;
  onClose: () => void; onNext: (item: ReviewItem) => void; onResolved: () => Promise<void>;
};
type Suggestion = { value: string; label: string; drive: Drive; title: string };

function ResolveForm({ item, next, api, onClose, onNext, onResolved }: ResolveProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  /** What is typed in the drive field, and the recorded drive it names when one was chosen. */
  const [typed, setTyped] = useState(item.mpn ?? '');
  const [drive, setDrive] = useState<Drive | null>(item.drive);
  const [condition, setCondition] = useState<string>(item.condition ?? '');
  const [capacity, setCapacity] = useState(item.capacity_gb === null ? '' : String(item.capacity_gb));
  const [right, setRight] = useState<'drive' | 'store'>('drive');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [search] = useDebouncedValue(typed.trim(), 250);
  useEffect(() => {
    if (search.length < 2 || search === drive?.mpn) { setSuggestions([]); return; }
    let active = true;
    api.drives({ q: search, in_stock: false, limit: 8, offset: 0 }).then(found => {
      if (active) setSuggestions(found.items.map(row => ({
        value: row.drive.mpn, drive: row.drive, title: row.representative.title,
        // Chosen, an option's label is what the field then holds: its MPN. renderOption shows the rest.
        label: row.drive.mpn,
      })));
    }).catch(() => { if (active) setSuggestions([]); });
    return () => { active = false; };
  }, [api, search, drive]);
  // The store and the recorded drive disagree on capacity: the reviewer says which is right.
  const disputed = drive !== null && item.capacity_gb !== null && item.capacity_gb !== drive.capacity_gb;
  const save = async (then: ReviewItem | null) => {
    const mpn = typed.trim();
    const problems: Record<string, string> = {};
    if (!mpn) problems.mpn = 'Name the drive by its MPN.';
    if (!condition) problems.condition = 'Choose a condition.';
    if (!drive && !capacity.trim()) problems.capacity = 'Enter the capacity of this new drive.';
    setErrors(problems);
    if (Object.keys(problems).length) return;
    setSaving(true); setError('');
    try {
      const correct = disputed && right === 'store';
      await api.decide(item.id, {
        decision: 'match', mpn, condition: condition as Condition,
        capacity_gb: drive ? (correct ? item.capacity_gb : null) : Number(capacity.trim()),
        correct_drive: correct,
      });
      await onResolved();
      if (then) onNext(then); else onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The offer could not be resolved.');
    } finally { setSaving(false); }
  };
  const differs = (store: string | null, recorded: string | null) => store !== null && recorded !== null && store !== recorded;
  const storeMpn = item.mpn, storeCapacity = item.capacity_gb === null ? null : capacityLabel(item.capacity_gb);
  const recordedCapacity = drive ? capacityLabel(drive.capacity_gb) : null;
  const cell = (value: string | null, other: string | null) => <Table.Td className="mono">{value ?? '—'}
    {differs(value, other) && <span className="differs">differs</span>}</Table.Td>;
  return <Modal opened title="Resolve offer" size="lg" onClose={() => { if (!saving) onClose(); }} centered>
    <form onSubmit={event => { event.preventDefault(); void save(null); }} noValidate><Stack>
      <a className="offer-link" href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a>
      <Text size="sm">{why(item, drive)}</Text>
      <Table aria-label="From the store and as recorded" className="evidence">
        <Table.Thead><Table.Tr><Table.Th /><Table.Th>From the store</Table.Th><Table.Th>Recorded drive</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>
          <Table.Tr><Table.Th scope="row">MPN</Table.Th>{cell(storeMpn, drive?.mpn ?? null)}<Table.Td className="mono">{drive?.mpn ?? '—'}</Table.Td></Table.Tr>
          <Table.Tr><Table.Th scope="row">Capacity</Table.Th>{cell(storeCapacity, recordedCapacity)}<Table.Td className="mono">{recordedCapacity ?? '—'}</Table.Td></Table.Tr>
        </Table.Tbody>
      </Table>
      <Autocomplete label="Drive" aria-label="Drive" required placeholder="MPN, or words from its name"
        description="Choose a recorded drive, or enter the MPN of a new one." value={typed} error={errors.mpn}
        data={suggestions} filter={({ options }) => options}
        renderOption={({ option }) => {
          const found = suggestions.find(suggestion => suggestion.value === option.value);
          return found && <span><span className="mono">{found.drive.mpn}</span>{' '}<span className="mono">{capacityLabel(found.drive.capacity_gb)}</span>{' '}{found.title}</span>;
        }}
        onChange={value => {
          setTyped(value);
          // The MPN of a drive found is that drive; the store's own MPN, the drive it named; any
          // other, a new drive.
          const chosen = suggestions.find(suggestion => suggestion.value === value.trim());
          setDrive(chosen ? chosen.drive : value.trim() === item.mpn ? item.drive : null);
        }} />
      <NativeSelect label="Condition" aria-label="Condition" required value={condition} error={errors.condition}
        data={[{ value: '', label: 'Choose condition' }, ...conditions]} onChange={event => setCondition(event.currentTarget.value)} />
      {disputed && <Radio.Group label="Which capacity is right?" value={right} onChange={value => setRight(value as 'drive' | 'store')}>
        <Stack gap="xs" mt="xs">
          <Radio value="drive" label={`The drive is right: record it as ${recordedCapacity}`} />
          <Radio value="store" label={`The store is right: correct the drive to ${storeCapacity}`} />
        </Stack>
      </Radio.Group>}
      {disputed && right === 'store' && <Text size="sm" className="warning-note">This changes the capacity of every offer of {drive.mpn}.</Text>}
      {!drive && <>
        <CapacityField value={capacity} onChange={setCapacity} error={errors.capacity} />
        <Text size="xs" c="dimmed">A new drive is recorded with this capacity.</Text>
      </>}
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={saving}>Cancel</Button>
        <Button type="submit" variant={next ? 'default' : 'filled'} loading={saving}>Save</Button>
        {next && <Button onClick={() => { void save(next); }} loading={saving}>Save and next</Button>}
      </Group>
    </Stack></form>
  </Modal>;
}
