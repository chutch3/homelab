import { useState } from 'react';
import { Alert, Button, Group, Modal, Stack, Text } from '@mantine/core';
import type { ListingsApi, Source } from './api';

type Props = { source: Source; api: ListingsApi; onClose: () => void; onDeleted: () => Promise<void> };

/** Confirms deleting a store. One that offers are recorded under is kept, and the dialog says so. */
export function DeleteSourceDialog({ source, api, onClose, onDeleted }: Props) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  return <Modal opened title="Delete store" onClose={() => { if (!deleting) onClose(); }} centered>
    <Stack>
      <Text>Delete {source.name} and its collector runs? This cannot be undone.</Text>
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={deleting}>Cancel</Button>
        <Button color="red" loading={deleting} onClick={async () => {
          setDeleting(true); setError('');
          try {
            await api.deleteSource(source.id);
            await onDeleted(); onClose();
          } catch (err) {
            setError(err instanceof Error ? err.message : 'The store could not be deleted.');
          } finally { setDeleting(false); }
        }}>Delete</Button>
      </Group>
    </Stack>
  </Modal>;
}
