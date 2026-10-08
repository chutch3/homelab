import { useState } from 'react';
import { Alert, Button, Group, Modal, NativeSelect, Stack, Table, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { Condition, ListingsApi, Store, UnmatchedItem, UnmatchedReason } from './api';
import { CapacityField } from './CapacityField';
import { conditions, dollars } from './listing-display';
import { Pager } from './Pager';

const reasons: Record<UnmatchedReason, string> = {
  missing_mpn: 'No MPN found',
  missing_condition: 'Condition not recognized',
  capacity_conflict: "Capacity doesn't match the drive",
  missing_capacity: 'New drive needs a capacity',
  missing_price: 'No price yet',
};

type Props = {
  /** The page of the queue being shown, of `total` offers in all. */
  items: UnmatchedItem[]; total: number; page: number; pageSize: number;
  onPage: (page: number) => void; onPageSize: (size: number) => void;
  /** The stores, to name the one each offer was read from. */
  stores: Store[];
  /** Why the offers could not be loaded, when they could not, and the way to load them again. */
  error?: string; onRetry?: () => void;
  api: ListingsApi; onChanged: () => Promise<void>;
};

/** Offers a collector read but could not place: each is resolved by naming its drive, or ignored. */
export function ReviewQueue({ items, total, page, pageSize, onPage, onPageSize, stores, error: loadError = '', onRetry, api, onChanged }: Props) {
  const [resolving, setResolving] = useState<UnmatchedItem | null>(null);
  /** The offer being asked about before it is ignored, by id: ignoring is not undone from here. */
  const [confirming, setConfirming] = useState<string | null>(null);
  const [ignoring, setIgnoring] = useState(false);
  const [error, setError] = useState('');
  const ignore = async (item: UnmatchedItem) => {
    setError(''); setIgnoring(true);
    try { await api.ignoreUnmatched(item.id); setConfirming(null); await onChanged(); }
    catch (err) { setError(err instanceof Error ? err.message : 'The offer could not be ignored.'); }
    finally { setIgnoring(false); }
  };
  return <section id="review-queue" aria-labelledby="review-queue-heading" className="admin-section panel">
    <h2 id="review-queue-heading">Needs matching{total > 0 && <span className="count"> ({total})</span>}</h2>
    <Stack gap="sm">
      {total > 0 && <Text size="sm" c="dimmed" className="section-note">Offers a collector read but could not match to a drive. Resolving one also teaches the collector for next time.</Text>}
      {error && <Alert color="red" role="alert">{error}</Alert>}
      {loadError ? <Alert color="red" role="alert"><Text size="sm" mb="sm">The offers to match could not be loaded: {loadError}</Text>
        <Button variant="default" onClick={onRetry}>Try again</Button></Alert>
      : items.length === 0 ? <Text size="sm" className="all-clear"><span aria-hidden="true">✓ </span>Nothing to match.</Text> : <Table aria-label="Offers to match" className="todo-list">
        <Table.Thead><Table.Tr><Table.Th>Offer</Table.Th><Table.Th>Why</Table.Th><Table.Th className="numeric">Price</Table.Th>
          <Table.Th>Store</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{items.map(item => <Table.Tr key={item.id}>
          <Table.Td className="todo-title"><a className="offer-link" href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a></Table.Td>
          <Table.Td data-label="Why">{reasons[item.reason]}</Table.Td>
          <Table.Td data-label="Price" className="mono">{item.item_price_cents === null ? '—' : dollars(item.item_price_cents)}</Table.Td>
          <Table.Td data-label="Store">{stores.find(store => store.key === item.source)?.name ?? item.source}</Table.Td>
          <Table.Td className="todo-actions">{confirming === item.id
            ? <Group gap="sm" wrap="nowrap"><Text size="sm">Ignore this offer?</Text>
              <Button color="red" loading={ignoring} onClick={() => ignore(item)}>Yes, ignore</Button>
              <Button variant="default" disabled={ignoring} onClick={() => setConfirming(null)}>Keep</Button></Group>
            : <Group gap="md" wrap="nowrap">
              <Button onClick={() => setResolving(item)}>Resolve</Button>
              <Button variant="subtle" onClick={() => setConfirming(item.id)}>Ignore</Button></Group>}</Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table>}
      <Pager label="Needs matching" page={page} total={total} pageSize={pageSize} onPage={onPage} onPageSize={onPageSize} />
    </Stack>
    {resolving && <ResolveForm item={resolving} api={api} onClose={() => setResolving(null)} onResolved={onChanged} />}
  </section>;
}

type ResolveProps = { item: UnmatchedItem; api: ListingsApi; onClose: () => void; onResolved: () => Promise<void> };

function ResolveForm({ item, api, onClose, onResolved }: ResolveProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const form = useForm({
    initialValues: {
      mpn: item.mpn ?? '', condition: item.condition ?? '',
      capacity: item.capacity_gb === null ? '' : String(item.capacity_gb),
    },
    validate: {
      mpn: value => value.trim() ? null : 'Enter the MPN.',
      condition: value => value ? null : 'Choose a condition.',
    },
  });
  const submit = form.onSubmit(async values => {
    setSaving(true); setError('');
    try {
      await api.resolveUnmatched(item.id, {
        mpn: values.mpn.trim(), condition: values.condition as Condition, capacity_gb: values.capacity.trim() ? Number(values.capacity.trim()) : null,
      });
      await onResolved(); onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The offer could not be resolved.');
    } finally { setSaving(false); }
  });
  return <Modal opened title="Resolve offer" onClose={() => { if (!saving) onClose(); }} centered>
    <form onSubmit={submit} noValidate><Stack>
      <Text size="sm">{item.title}</Text>
      <TextInput label="MPN" aria-label="MPN" required {...form.getInputProps('mpn')} />
      <NativeSelect label="Condition" aria-label="Condition" required
        data={[{ value: '', label: 'Choose condition' }, ...conditions]} {...form.getInputProps('condition')} />
      <CapacityField value={form.values.capacity} onChange={capacity => form.setFieldValue('capacity', capacity)} />
      <Text size="xs" c="dimmed">Capacity is needed only when this MPN is new.</Text>
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={saving}>Cancel</Button>
        <Button type="submit" loading={saving}>Save</Button>
      </Group>
    </Stack></form>
  </Modal>;
}
