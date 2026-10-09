import { Table, Text } from '@mantine/core';
import type { ListingsApi, ListingSummary } from './api';
import { dollars, sellerLabel } from './listing-display';
import { PriceCheck } from './PriceCheck';

type Props = {
  /** Hand-entered offers overdue for a check, oldest first. */
  offers: ListingSummary[]; recentDays: number;
  api: ListingsApi; nextId: () => string;
  onChanged: (notice?: string) => Promise<void>;
};

const dateLabel = (value: string) => new Date(value).toLocaleString();

/** Offers only a person keeps current: open each store page, then record what it says in one step. */
export function RecheckQueue({ offers, recentDays, api, nextId, onChanged }: Props) {
  return <section aria-labelledby="recheck-heading" className="admin-section panel">
    <h2 id="recheck-heading">Recheck by hand{offers.length > 0 && <span className="count"> ({offers.length})</span>}</h2>
    {offers.length === 0 ? <Text size="sm" className="all-clear"><span aria-hidden="true">✓ </span>Everything entered by hand has been checked recently.</Text>
      : <><Text size="sm" c="dimmed" className="section-note">Offers you entered by hand, not checked in {recentDays} days. Open each store page, then record what it shows.</Text>
      <Table aria-label="Offers to recheck" className="todo-list">
        <Table.Thead><Table.Tr><Table.Th>Offer</Table.Th><Table.Th>Store</Table.Th><Table.Th>Last checked</Table.Th>
          <Table.Th className="numeric">Last price</Table.Th><Table.Th>What it shows now</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{offers.map(listing => <Table.Tr key={listing.id}>
          <Table.Td className="todo-title">{listing.title}</Table.Td>
          <Table.Td data-label="Store">{sellerLabel(listing)}</Table.Td>
          <Table.Td data-label="Last checked"><time dateTime={listing.last_checked_at}>{dateLabel(listing.last_checked_at)}</time></Table.Td>
          <Table.Td data-label="Last price" className="mono">{listing.latest.in_stock ? dollars(listing.latest.item_price_cents) : 'Out of stock'}</Table.Td>
          <Table.Td className="todo-actions"><PriceCheck listing={listing} api={api} nextId={nextId} onRecorded={onChanged} /></Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></>}
  </section>;
}
