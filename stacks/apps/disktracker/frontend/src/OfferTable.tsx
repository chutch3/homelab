import { Fragment, type ReactNode } from 'react';
import { ActionIcon, Button, Group, Menu, Table, Text, VisuallyHidden } from '@mantine/core';
import type { Offer } from './api';
import { ageLabel } from './admin-overview';
import { dollars, sellerLabel } from './listing-display';
import { amountText, priceChange } from './price-change';

const dateLabel = (value: string) => new Date(value).toLocaleString();
type Props = {
  listings: Offer[]; lowestId: string | null;
  /** The moment each offer's last check is aged from. */
  now: Date;
  /** The offer whose price check is open under its row, by id; Record price opens and closes it. */
  checking: string | null; onCheck: (id: string | null) => void;
  /** The price check shown under the offer being checked. */
  check: (listing: Offer) => ReactNode;
  /** Corrections; without them the row has no ⋯ menu. */
  onEdit?: (listing: Offer) => void; onDelete?: (listing: Offer) => void;
};

/** One condition's offers, a row for each store: what a terabyte costs there, the total, how long
 * ago it was checked, and the ways to the store and to recording what it says now. */
export function OfferTable({ listings, lowestId, now, checking, onCheck, check, onEdit, onDelete }: Props) {
  return <div className="sheet-scroll"><Table aria-label="Offers" className="offers">
    <Table.Thead><Table.Tr><Table.Th>Store</Table.Th><Table.Th className="numeric">$/TB</Table.Th>
      <Table.Th className="numeric">Total</Table.Th><Table.Th>Checked</Table.Th><Table.Th><VisuallyHidden>Actions</VisuallyHidden></Table.Th></Table.Tr></Table.Thead>
    <Table.Tbody>{listings.map(listing => {
      const { latest } = listing;
      const moved = priceChange(listing.observations), change = amountText(moved);
      // Green for a fall and red for a rise; the arrow says the same without colour.
      const direction = !moved.difference ? '' : moved.difference < 0 ? ' price-fell' : ' price-rose';
      const open = checking === listing.id;
      return <Fragment key={listing.id}><Table.Tr>
        <Table.Td data-label="Store"><strong>{sellerLabel(listing)}</strong>
          {/* The store's own name for it: drives are named the same everywhere, offers as sold. */}
          <div className="secondary offer-title">{listing.title}</div></Table.Td>
        <Table.Td data-label="$/TB" className="numeric"><strong className="unit-price">{`$${latest.price_per_tb}`}</strong></Table.Td>
        <Table.Td data-label="Total" className="numeric">{dollars(latest.total_cents)}
          {!latest.shipping_known && <Text size="xs" c="dimmed">+ shipping</Text>}
          {change && <Text size="xs" className={`mono${direction}`}>{change}</Text>}
          {listing.id === lowestId && <div><span className="tag lowest">Lowest</span></div>}
          {!latest.in_stock && <div><span className="tag">Out of stock</span></div>}</Table.Td>
        <Table.Td data-label="Checked" className="secondary"><time dateTime={listing.last_checked_at} title={dateLabel(listing.last_checked_at)}>{ageLabel(now.getTime() - Date.parse(listing.last_checked_at))} ago</time></Table.Td>
        <Table.Td className="offer-actions"><Group gap="sm" wrap="wrap" justify="end">
          {listing.url && <Button component="a" href={listing.url} target="_blank" rel="noopener noreferrer">View at store<span aria-hidden="true">&nbsp;↗</span></Button>}
          <Button variant={open ? 'light' : 'default'} aria-expanded={open} onClick={() => onCheck(open ? null : listing.id)}>Record price</Button>
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
