import { Button, Table } from '@mantine/core';
import type { Listing, Observation } from './api';
import { combinedObservations } from './drive-observations';
import { dollars, sellerLabel } from './listing-display';

const dateLabel = (value: string) => new Date(value).toLocaleString();
/** Without onDelete, prices are shown but cannot be deleted. */
type Props = { listings: Listing[]; onDelete?: (listing: Listing, observation: Observation) => void };

export function DriveObservationTable({ listings, onDelete }: Props) {
  const rows = combinedObservations(listings);
  return <div className="sheet-scroll"><Table aria-label="Price history" mt="sm">
    <Table.Thead><Table.Tr><Table.Th>Store</Table.Th><Table.Th>Checked</Table.Th><Table.Th>Item</Table.Th><Table.Th>Shipping & fees</Table.Th><Table.Th>Total</Table.Th><Table.Th>Notes</Table.Th>{onDelete && <Table.Th>Actions</Table.Th>}</Table.Tr></Table.Thead>
    <Table.Tbody>{rows.map(({ listing, observation }) => <Table.Tr key={observation.id}>
      <Table.Td>{sellerLabel(listing)}</Table.Td>
      <Table.Td><time dateTime={observation.observed_at}>{dateLabel(observation.observed_at)}</time></Table.Td>
      <Table.Td>{dollars(observation.item_price_cents)}</Table.Td><Table.Td>{observation.shipping_cents === null ? 'Not included' : dollars(observation.shipping_cents)}</Table.Td>
      <Table.Td>{dollars(observation.total_cents)}</Table.Td><Table.Td>{observation.notes || '—'}</Table.Td>
      {onDelete && <Table.Td><Button variant="subtle" color="red" onClick={() => onDelete(listing, observation)}>Delete price</Button></Table.Td>}
    </Table.Tr>)}</Table.Tbody>
  </Table></div>;
}
