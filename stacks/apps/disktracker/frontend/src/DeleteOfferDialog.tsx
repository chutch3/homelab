import { useState } from 'react';
import { Alert, Button, Group, Modal, Stack, Text } from '@mantine/core';
import type { Listing, ListingsApi } from './api';
import { conditionLabel, sellerLabel } from './listing-display';

type Props = { listing: Listing; api: ListingsApi; onClose: () => void; onDeleted: () => Promise<void> };

export function DeleteOfferDialog({ listing, api, onClose, onDeleted }: Props) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const prices = listing.observations.length;
  return <Modal opened title="Delete offer" onClose={() => { if (!deleting) onClose(); }} centered>
    <Stack>
      <Text>Delete {listing.title} · {sellerLabel(listing)} · {conditionLabel(listing.condition)} and its {prices} price{prices === 1 ? '' : 's'}?</Text>
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={deleting}>Cancel</Button>
        <Button color="red" loading={deleting} onClick={async () => {
          setDeleting(true); setError('');
          try {
            await api.deleteOffer(listing.id);
            await onDeleted(); onClose();
          } catch (err) {
            setError(err instanceof Error ? err.message : 'The offer could not be deleted.');
          } finally { setDeleting(false); }
        }}>Delete</Button>
      </Group>
    </Stack>
  </Modal>;
}
