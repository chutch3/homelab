import { useState } from 'react';
import { Alert, Button, Group, Stack, Text, TextInput } from '@mantine/core';
import type { InspectionCandidate, ListingsApi, SourceInspection, SourceTransport } from './api';
import { SourcePreviewResult } from './SourcePreviewResult';

type Props = {
  api: ListingsApi; transport: SourceTransport;
  /** Told the way of reading the store that was chosen, the store's address, and the link inspected. */
  onUse: (candidate: InspectionCandidate, baseUrl: string, link: string) => void;
};

/** Finds out how a store not read yet would be read, from a link to one of its product pages: each way
 * that reads a drive from the page is shown with that drive, and can be taken as the store's settings. */
export function LinkInspector({ api, transport, onUse }: Props) {
  const [link, setLink] = useState('');
  const [inspecting, setInspecting] = useState(false);
  const [found, setFound] = useState<SourceInspection | null>(null);
  const [error, setError] = useState('');
  const inspect = async () => {
    setInspecting(true); setFound(null); setError('');
    try { setFound(await api.inspectLink(link.trim(), transport)); }
    catch (err) { setError(err instanceof Error ? err.message : 'The link could not be inspected.'); }
    setInspecting(false);
  };
  return <Stack gap="xs" className="link-inspector">
    <Group align="flex-end" wrap="nowrap">
      <TextInput label="Product link" aria-label="Product link" type="url" style={{ flex: 1 }} value={link}
        placeholder="https://www.example.com/a-drive" onChange={event => setLink(event.currentTarget.value)}
        description="Optional: a link to one drive at the store, to work out its settings from" />
      <Button variant="default" onClick={inspect} loading={inspecting} disabled={!link.trim()}>Inspect</Button>
    </Group>
    {error && <Alert color="red" role="alert">{error}</Alert>}
    {found?.status === 'failed' && <Alert color="red">The page could not be read: {found.reason}</Alert>}
    {found?.status === 'nothing' && <Alert color="yellow">The page was read, but no way of reading a drive from it was found.
      {found.notes.length > 0 && <ul className="source-preview-notes">{found.notes.map((note, index) => <li key={index}>{note}</li>)}</ul>}
    </Alert>}
    {found?.candidates.map((candidate, index) => <div key={index} className="inspection-candidate">
      <SourcePreviewResult label="Inspection result" notesLabel="Why these settings" store={candidate.summary}
        lead={`${candidate.offers} ${candidate.offers === 1 ? 'offer' : 'offers'} read with these settings; the first:`}
        preview={{ status: 'found', reason: null, offer: candidate.offer, verdict: candidate.verdict, notes: candidate.evidence }} />
      <Button size="compact-sm" mt="xs" onClick={() => onUse(candidate, found.base_url, link.trim())}>Use these settings</Button>
    </div>)}
    {found?.status === 'found' && <Text size="xs" c="dimmed">These are worked out from one page: check them with Test before saving.</Text>}
  </Stack>;
}
