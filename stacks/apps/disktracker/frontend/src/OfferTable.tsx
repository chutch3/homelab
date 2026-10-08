import { Fragment, type ReactNode } from 'react';
import { ActionIcon, Button, Group, Menu, Table, Text, VisuallyHidden } from '@mantine/core';
import type { Listing } from './api';
import { dollars, sellerLabel } from './listing-display';
import { amountText, priceChange } from './price-change';

const dateLabel = (value: string) => new Date(value).toLocaleString();
type Props = {
  listings: Listing[]; lowestId: string | null;
  /** The offer whose price check is open under its row, by id; Record price opens and closes it. */
  checking: string | null; onCheck: (id: string | null) => void;
  /** The price check shown under the offer being checked. */
  check: (listing: Listing) => ReactNode;
  /** Corrections; without them the row has no ⋯ menu. */
  onEdit?: (listing: Listing) => void; onDelete?: (listing: Listing) => void;
};

export function OfferTable({ listings, lowestId, checking, onCheck, check, onEdit, onDelete }: Props) {
  return <div className="sheet-scroll"><Table aria-label="Offers" className="offers">
    <Table.Thead><Table.Tr><Table.Th>Store</Table.Th><Table.Th className="numeric">$/TB</Table.Th>
      <Table.Th className="numeric">Total</Table.Th><Table.Th>Checked</Table.Th><Table.Th><VisuallyHidden>Actions</VisuallyHidden></Table.Th></Table.Tr></Table.Thead>
    <Table.Tbody>{listings.map(listing => {
      const { latest } = listing;
      const change = amountText(priceChange(listing.observations));
      const open = checking === listing.id;
      return <Fragment key={listing.id}><Table.Tr>
        <Table.Td data-label="Store"><strong>{sellerLabel(listing)}</strong></Table.Td>
        <Table.Td data-label="$/TB" className="numeric"><strong className="unit-price">{`$${latest.price_per_tb}`}</strong></Table.Td>
        <Table.Td data-label="Total" className="numeric">{dollars(latest.total_cents)}
          {!latest.shipping_known && <Text size="xs" c="dimmed">Shipping not included</Text>}
          {change && <Text size="xs" className="mono">{change}</Text>}
          {listing.id === lowestId && <div><span className="tag lowest">Lowest price</span></div>}
          {!latest.in_stock && <div><span className="tag">Out of stock</span></div>}</Table.Td>
        <Table.Td data-label="Checked" className="secondary"><time dateTime={listing.last_checked_at}>{dateLabel(listing.last_checked_at)}</time></Table.Td>
        <Table.Td className="offer-actions"><Group gap="sm" wrap="wrap" justify="end">
          {listing.url && <a className="seller-link" href={listing.url} target="_blank" rel="noopener noreferrer">Open store page ↗</a>}
          <Button variant={open ? 'filled' : 'default'} aria-expanded={open} onClick={() => onCheck(open ? null : listing.id)}>Record price</Button>
          {onEdit && onDelete && <Menu position="bottom-end">
            <Menu.Target><ActionIcon variant="default" aria-label={`More actions for ${sellerLabel(listing)}`}>⋯</ActionIcon></Menu.Target>
            <Menu.Dropdown>
              <Menu.Item onClick={() => onEdit(listing)}>Edit offer</Menu.Item>
              <Menu.Item color="red" onClick={() => onDelete(listing)}>Delete offer</Menu.Item>
            </Menu.Dropdown>
          </Menu>}
        </Group></Table.Td>
      </Table.Tr>
      {open && <Table.Tr className="check-row"><Table.Td colSpan={5}>{check(listing)}</Table.Td></Table.Tr>}</Fragment>;
    })}</Table.Tbody>
  </Table></div>;
}
