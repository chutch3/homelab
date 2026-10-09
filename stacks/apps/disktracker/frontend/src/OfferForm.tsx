import { useState } from 'react';
import { Alert, Button, Group, Modal, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { Listing, ListingsApi } from './api';
import { textError, urlError } from './entry-validation';
import { conditionLabel, sellerLabel } from './listing-display';

type Props = { listing: Listing; api: ListingsApi; onClose: () => void; onSaved: () => Promise<void> };

export function OfferForm({ listing, api, onClose, onSaved }: Props) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const form = useForm({
    initialValues: { title: listing.title, url: listing.url ?? '' },
    validate: {
      title: value => textError(value, 160, 'Enter the offer title.'),
      url: urlError,
    },
  });
  const submit = form.onSubmit(async values => {
    setSaving(true); setError('');
    try {
      await api.editOffer(listing.id, { title: values.title.trim(), url: values.url.trim() || null });
      await onSaved(); onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The offer could not be saved.');
    } finally { setSaving(false); }
  });
  return <Modal opened title="Edit offer" onClose={() => { if (!saving) onClose(); }} centered>
    <form onSubmit={submit} noValidate><Stack>
      <Text size="sm" c="dimmed">{listing.mpn} · {sellerLabel(listing)} · {conditionLabel(listing.condition)}</Text>
      <TextInput label="Offer title" aria-label="Offer title" required maxLength={160} {...form.getInputProps('title')} />
      <TextInput label="Store page URL" aria-label="Store page URL" type="url" {...form.getInputProps('url')} />
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={saving}>Cancel</Button>
        <Button type="submit" loading={saving}>Save</Button>
      </Group>
    </Stack></form>
  </Modal>;
}
