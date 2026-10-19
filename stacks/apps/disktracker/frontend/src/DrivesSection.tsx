import { useCallback, useState } from 'react';
import { Alert, Button, Table, Text, TextInput } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import type { CatalogDriveQuery, DisktrackerApi, DriveIssue } from './api';
import { issueLabel, issues } from './admin-overview';
import { capacityLabel, driveName } from './listing-display';
import { Pager } from './Pager';
import { useServedPages } from './paging';

type Filter = { q: string; issue: DriveIssue | null };

type Props = {
  api: DisktrackerApi; storage: Pick<Storage, 'getItem' | 'setItem'>; recentDays: number;
  /** Counts changes made anywhere: the drives are asked for again after each. */
  revision: number;
  /** Opens a drive, by its key and the title it is named by. */
  onSelect: (key: string, title: string) => void;
};

/** Every drive to correct, held offers and all, as the server finds, orders and pages them: by
 * any name an offer of it goes by, and by what it needs. */
export function DrivesSection({ api, storage, recentDays, revision, onSelect }: Props) {
  const [typed, setTyped] = useState('');
  // Asked for once the words stop changing, not at every letter.
  const [q] = useDebouncedValue(typed.trim(), 300);
  const [issue, setIssue] = useState<DriveIssue | null>(null);
  const serve = useCallback(({ q, issue }: Filter, limit: number, offset: number) => {
    const query: CatalogDriveQuery = { q, ...(issue ? { issue } : {}), recent_days: recentDays, limit, offset };
    return api.catalogDrives(query);
  }, [api, recentDays]);
  const { found, page, size, error, setPage, setSize, retry } = useServedPages(serve, { q, issue }, storage, 'drives', revision);
  return <section aria-labelledby="drives-heading" className="admin-section">
    <h2 id="drives-heading">Drives</h2>
    <div className="drive-tools">
      <TextInput label="Search drives" aria-label="Search drives" placeholder="Name, MPN or store" w={360} maw="100%"
        value={typed} onChange={event => setTyped(event.currentTarget.value)} />
      {issues.map(value => <button key={value} type="button" className="chip toggle" aria-pressed={issue === value}
        onClick={() => setIssue(issue === value ? null : value)}>
        {issueLabel(value)}{found && ` (${found.issues[value]})`}</button>)}
    </div>
    {error ? <Alert color="red" role="alert"><Text size="sm" mb="sm">The drives could not be loaded: {error}</Text>
      <Button variant="default" onClick={retry}>Try again</Button></Alert>
    : !found ? <Text size="sm" c="dimmed" role="status" aria-label="Loading drives">Loading…</Text>
    : found.all === 0 ? <Text size="sm" c="dimmed">No drives yet.</Text> : <>
      <Text size="sm" c="dimmed" mb="xs">{found.total} of {found.all} drives{issue && ` · ${issueLabel(issue)}`}</Text>
      <div className="sheet-scroll"><Table aria-label="Drives" verticalSpacing="sm">
        <Table.Thead><Table.Tr><Table.Th>Drive</Table.Th><Table.Th>MPN</Table.Th><Table.Th className="numeric">Capacity</Table.Th>
          <Table.Th className="numeric">Offers</Table.Th><Table.Th>Needs attention</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{found.items.map(row => <Table.Tr key={row.drive.id} className="drive-row" onClick={() => onSelect(`drive:${row.drive.id}`, row.title)}>
          <Table.Td><button type="button" className="drive-link" title={row.title}>{driveName(row.drive)}</button></Table.Td>
          <Table.Td className="mono">{row.drive.mpn}</Table.Td>
          <Table.Td className="numeric">{capacityLabel(row.drive.capacity_gb)}</Table.Td>
          <Table.Td className="numeric">{row.offers}</Table.Td>
          <Table.Td className="secondary">{row.issues.map(issueLabel).join(', ') || '—'}</Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></div>
    </>}
    <Pager label="Drives" page={page} total={found?.total ?? 0} pageSize={size} onPage={setPage} onPageSize={setSize} />
  </section>;
}
