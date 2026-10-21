import { useEffect, useState } from 'react';
import { Alert, Autocomplete, Button, Group, Modal, Stack, Text } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import type { DisktrackerApi, Drive, FoundDrive } from './api';
import { capacityLabel } from './listing-display';

type Props = {
  /** The drive that stays: the other is merged into it. */
  drive: Drive; api: DisktrackerApi; nextId: () => string;
  onClose: () => void; onMerged: (absorbed: Drive) => Promise<void>;
};

const listed = (names: string[]) => names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;

/** Merging another drive into this one, the one way two drives become one: the other drive is found by any name an
 * offer of it goes by, and what becomes of both is said before anything is merged. */
export function MergeDriveForm({ drive, api, nextId, onClose, onMerged }: Props) {
  const [typed, setTyped] = useState('');
  const [found, setFound] = useState<FoundDrive[]>([]);
  /** The drive chosen, with the save key its merge goes under: a retry of the same merge sends the same one. */
  const [source, setSource] = useState<{ drive: Drive; key: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [search] = useDebouncedValue(typed.trim(), 250);
  useEffect(() => {
    if (search.length < 2) { setFound([]); return; }
    let active = true;
    api.findDrives({ q: search, limit: 8, offset: 0 })
      // Never this drive itself.
      .then(page => { if (active) setFound(page.items.filter(row => row.drive.id !== drive.id)); })
      .catch(() => { if (active) setFound([]); });
    return () => { active = false; };
  }, [api, search, drive.id]);
  const merge = async () => {
    if (!source) return;
    setSaving(true); setError('');
    try {
      await api.mergeDrive(source.drive.id, drive.id, source.key);
      await onMerged(source.drive);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The drives could not be merged.');
    } finally { setSaving(false); }
  };
  const absorbed = source?.drive;
  const brand = drive.brand ?? absorbed?.brand ?? null;
  return <Modal opened title="Merge another drive into this one" size="lg" centered onClose={() => { if (!saving) onClose(); }}>
    <Stack>
      <Text size="sm">{drive.mpn} stays. The drive merged in is gone, and its offers are this drive's.</Text>
      <Autocomplete label="Drive to merge in" aria-label="Drive to merge in" placeholder="MPN, or words from its name"
        value={typed} data={found.map(row => row.drive.mpn)} filter={({ options }) => options}
        renderOption={({ option }) => {
          const row = found.find(candidate => candidate.drive.mpn === option.value);
          return row && <span><span className="mono">{row.drive.mpn}</span>{' '}<span className="mono">{capacityLabel(row.drive.capacity_gb)}</span>{' '}{row.title}</span>;
        }}
        onChange={value => {
          setTyped(value); setError('');
          const chosen = found.find(row => row.drive.mpn === value.trim());
          setSource(current => chosen ? (current?.drive.id === chosen.drive.id ? current : { drive: chosen.drive, key: nextId() }) : null);
        }} />
      {absorbed && <>
        <Text size="sm">{drive.mpn} stays, going by {listed([absorbed.mpn, ...absorbed.aliases])} too, with {brand ? `the brand ${brand}` : 'no brand'}.</Text>
        <Text size="sm" c="dimmed">Every offer of {absorbed.mpn} moves to it; one at the same store, from the same seller, in the same
          condition as one of its own joins that offer, with both price histories. This cannot be undone.</Text>
      </>}
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={saving}>Cancel</Button>
        <Button color="red" disabled={!absorbed} loading={saving} onClick={() => { void merge(); }}>Merge</Button>
      </Group>
    </Stack>
  </Modal>;
}
