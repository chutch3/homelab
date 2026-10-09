import { useState } from 'react';
import { Alert, Button, Group, Modal, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { ApiValidationError, type Drive, type ListingsApi } from './api';
import { CapacityField } from './CapacityField';
import { capacityError } from './entry-validation';
import { SpecificationFields } from './SpecificationFields';
import type { Specifications } from './specifications';

type Props = {
  drive: Drive; api: ListingsApi; onClose: () => void; onSaved: (drive: Drive) => void;
  onAliasAdded?: () => Promise<void>;
};

export function DriveForm({ drive, api, onClose, onSaved, onAliasAdded }: Props) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [aliases, setAliases] = useState(drive.aliases);
  const [alias, setAlias] = useState('');
  const [aliasError, setAliasError] = useState('');
  const addAlias = async () => {
    setAliasError('');
    try {
      const updated = await api.addAlias(drive.id, alias.trim());
      setAliases(updated.aliases); setAlias('');
      await onAliasAdded?.();
    } catch (err) {
      setAliasError(err instanceof Error ? err.message : 'The MPN could not be added.');
    }
  };
  const form = useForm<{ capacity: string; brand: string; specifications: Specifications }>({
    validate: { capacity: capacityError },
    initialValues: { capacity: String(drive.capacity_gb), brand: drive.brand ?? '', specifications: drive.specifications },
  });
  const submit = form.onSubmit(async values => {
    setError(''); setSaving(true);
    try {
      const saved = await api.replaceSpecifications(drive.id, {
        capacity_gb: Number(values.capacity.trim()), specifications: values.specifications, brand: values.brand.trim(),
      });
      onSaved(saved); onClose();
    } catch (err) {
      const { capacity_gb: capacity, brand, ...unplaced } = err instanceof ApiValidationError ? err.fields : {};
      if (capacity) form.setFieldError('capacity', capacity);
      if (brand) form.setFieldError('brand', brand);
      if (!(capacity || brand) || Object.keys(unplaced).length) {
        setError(err instanceof Error ? err.message : 'The specifications could not be saved.');
      }
    } finally { setSaving(false); }
  });
  return <Modal opened onClose={() => { if (!saving) onClose(); }} title="Edit specifications" size="lg" centered>
    <form onSubmit={submit} noValidate>
      <Stack gap="md">
        <Text size="sm" c="dimmed">Applies to every offer of MPN {drive.mpn}.</Text>
        <CapacityField value={form.values.capacity} error={form.errors.capacity}
          onChange={capacity => form.setFieldValue('capacity', capacity)} />
        <TextInput label="Brand" aria-label="Brand" maxLength={60} placeholder="e.g. Seagate"
          description="The drive's maker. Leave blank for the collector to name it." {...form.getInputProps('brand')} />
        <SpecificationFields value={form.values.specifications} onChange={value => form.setFieldValue('specifications', value)} />
        <Stack gap="xs">
          <Text size="sm" fw={500}>Other MPNs</Text>
          <Text size="xs" c="dimmed">Prices recorded under these MPNs join this drive; a drive already recorded under one is merged in.</Text>
          {aliases.length > 0 && <Group gap="xs">{aliases.map(value => <span key={value} className="tag mono">{value}</span>)}</Group>}
          <Group align="end">
            <TextInput label="Other MPN" aria-label="Other MPN" value={alias} error={aliasError}
              onChange={event => setAlias(event.currentTarget.value)} />
            <Button variant="default" disabled={!alias.trim()} onClick={addAlias}>Add MPN</Button>
          </Group>
        </Stack>
        {error && <Alert color="red" role="alert">{error}</Alert>}
        <Group justify="flex-end"><Button variant="default" onClick={onClose} disabled={saving}>Cancel</Button><Button type="submit" loading={saving}>Save</Button></Group>
      </Stack>
    </form>
  </Modal>;
}
