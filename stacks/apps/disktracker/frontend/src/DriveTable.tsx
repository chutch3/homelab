import { Table } from '@mantine/core';
import type { Condition, Observation } from './api';
import { ageLabel } from './admin-overview';
import { conditionChoices, priceLabel } from './drive-conditions';
import type { DriveGroup } from './drive-groups';
import { capacityLabel, conditionLabel, dollars, sellerLabel } from './listing-display';
import { isRecent, type Sort } from './listing-query';

type Props = {
  groups: DriveGroup[]; sort: Sort; onSort: (sort: Sort) => void;
  /** Opens a drive on a condition: the row's own, or another the drive is sold in, named on the row. */
  onSelect: (key: string, condition: Condition) => void;
  now: Date; recentDays: number; leaders: { total: Set<string>; unit: Set<string> };
};

/** What shipping adds to the item price, or that the total leaves it out. */
function shippingLabel({ shipping_known, shipping_cents }: Observation): string {
  if (!shipping_known || shipping_cents === null) return 'Shipping not included';
  return shipping_cents === 0 ? 'Free shipping' : `+${dollars(shipping_cents)} shipping`;
}

/** One row per drive, showing its cheapest offer and naming the other conditions it is sold in;
 * anywhere on a row opens the drive on the row's condition, and a condition named opens it on that. */
export function DriveTable({ groups, sort, onSort, onSelect, now, recentDays, leaders }: Props) {
  const heading = (column: string, label: string, numeric = false) => {
    const active = sort.startsWith(`${column}-`), ascending = sort.endsWith('-asc');
    const next = `${column}-${active && ascending ? 'desc' : 'asc'}` as Sort;
    return <Table.Th className={numeric ? 'numeric' : undefined} aria-sort={active ? ascending ? 'ascending' : 'descending' : 'none'}>
      <button className="sort-button" onClick={() => onSort(next)}>{label}{active && <span aria-hidden="true"> {ascending ? '↑' : '↓'}</span>}</button>
    </Table.Th>;
  };
  return <div className="sheet-scroll"><Table className="price-sheet" aria-label="Drive prices" verticalSpacing="sm">
    <Table.Thead><Table.Tr><Table.Th>Drive</Table.Th>{heading('capacity', 'Capacity')}<Table.Th>Condition</Table.Th>{heading('unit', '$/TB', true)}{heading('total', 'Total', true)}{heading('checked', 'Checked')}</Table.Tr></Table.Thead>
    <Table.Tbody>{groups.map(group => {
      const listing = group.representative, { latest } = listing;
      const age = now.getTime() - Date.parse(listing.last_checked_at);
      // One store can sell a drive in several conditions: stores are counted, not offers.
      const stores = new Set(group.listings.map(sellerLabel)).size;
      const others = conditionChoices(group.listings).filter(choice => choice.condition !== listing.condition);
      return <Table.Tr key={group.key} className="drive-row" onClick={() => onSelect(group.key, listing.condition)}>
        <Table.Td data-label="Drive"><button type="button" className="drive-link">{listing.title}</button>
          <div className="secondary mono">{listing.mpn ?? 'MPN unconfirmed'}</div>
          <div className="secondary">{stores > 1 && <><span>{stores} stores</span>{' · from '}</>}{sellerLabel(listing)}</div>
          {others.length > 0 && <div className="also"><span className="secondary">Also</span>{others.map(choice =>
            <button key={choice.condition} type="button" className="also-condition"
              onClick={event => { event.stopPropagation(); onSelect(group.key, choice.condition); }}>{choice.label} <span className="mono">{priceLabel(choice)}</span></button>)}</div>}</Table.Td>
        <Table.Td data-label="Capacity" className="mono">{capacityLabel(listing.capacity_gb)}</Table.Td>
        <Table.Td data-label="Condition">{conditionLabel(listing.condition)}</Table.Td>
        <Table.Td data-label="$/TB" className="numeric"><strong className="unit-price">{`$${latest.price_per_tb}`}</strong>
          {leaders.unit.has(listing.id) && <div><span className="tag lowest" title={`Among offers in stock and checked within ${recentDays} days`}>Lowest $/TB</span></div>}</Table.Td>
        <Table.Td data-label="Total" className="numeric">{dollars(latest.total_cents)}
          <div className="secondary">{shippingLabel(latest)}</div>
          {leaders.total.has(listing.id) && <div><span className="tag lowest" title={`Among offers in stock and checked within ${recentDays} days`}>Lowest total</span></div>}</Table.Td>
        <Table.Td data-label="Checked" className="checked">
          <time dateTime={listing.last_checked_at} title={new Date(listing.last_checked_at).toLocaleString()}>{age < 0 ? 'Future date' : `${ageLabel(age)} ago`}</time>
          {!isRecent(listing, now, recentDays) && <div><span className="tag stale" title={`Not checked in ${recentDays} days`}>Stale</span></div>}
          {!latest.in_stock && <div><span className="tag">Out of stock</span></div>}</Table.Td>
      </Table.Tr>;
    })}</Table.Tbody>
  </Table></div>;
}
