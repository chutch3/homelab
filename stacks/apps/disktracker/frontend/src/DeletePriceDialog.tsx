import { useState } from 'react';
import { Alert, Button, Group, Modal, Stack, Text } from '@mantine/core';
import type { Listing, ListingsApi, Observation } from './api';
import { dollars, sellerLabel } from './listing-display';

type Props = {
  listing: Listing; observation: Observation; api: ListingsApi;
  onClose: () => void; onDeleted: () => Promise<void>;
};

export function DeletePriceDialog({ listing, observation, api, onClose, onDeleted }: Props) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const onlyPrice = listing.observations.length === 1;
  return <Modal opened title="Delete price" onClose={() => { if (!deleting) onClose(); }} centered>
    <Stack>
      <Text>Delete the {dollars(observation.item_price_cents)} from {sellerLabel(listing)} checked {new Date(observation.observed_at).toLocaleString()}?</Text>
      {onlyPrice && <Text size="sm">This is the offer's only price, so the offer is removed too.</Text>}
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={deleting}>Cancel</Button>
        <Button color="red" loading={deleting} onClick={async () => {
          setDeleting(true); setError('');
          try {
            await api.deletePrice(listing.id, observation.id);
            await onDeleted(); onClose();
          } catch (err) {
            setError(err instanceof Error ? err.message : 'The price could not be deleted.');
          } finally { setDeleting(false); }
        }}>Delete</Button>
      </Group>
    </Stack>
  </Modal>;
}
