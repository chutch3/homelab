import { NativeSelect, Table } from '@mantine/core';
import type { Condition, Observation, PriceRange } from './api';
import { ageLabel } from './admin-overview';
import { marketChoices, priceLabel } from './drive-conditions';
import type { DriveGroup } from './drive-groups';
import { capacityLabel, conditionLabel, dollars, doubts, driveName, sellerLabel } from './listing-display';
import { isRecent, periods, type Period, type Sort } from './listing-query';
import { PriceRangeBar } from './PriceRangeBar';

type Props = {
  groups: DriveGroup[]; sort: Sort; onSort: (sort: Sort) => void;
  /** Opens a drive on a condition: the row's own, or another the drive is sold in, named on the row. */
  onSelect: (key: string, condition: Condition) => void;
  now: Date; recentDays: number; leaders: { total: Set<string>; unit: Set<string> };
  /** Each drive's price range over the last rangeDays, by its group key; a drive is missing until its prices are loaded. */
  ranges: Record<string, PriceRange>; rangeDays: Period; onRangeDays: (days: Period) => void;
};

/** What of the total is shipping, or that the total leaves it out; nothing when it is free, as it mostly is. */
function shippingLabel({ shipping_known, shipping_cents }: Observation): string {
  if (!shipping_known || shipping_cents === null) return '+ shipping';
  return shipping_cents === 0 ? '' : `incl. ${dollars(shipping_cents)} shipping`;
}

/** One row per drive, showing its cheapest offer and naming the other conditions it is sold in;
 * anywhere on a row opens the drive on the row's condition, and a condition named opens it on that. */
export function DriveTable({ groups, sort, onSort, onSelect, now, recentDays, leaders, ranges, rangeDays, onRangeDays }: Props) {
  const heading = (column: string, label: string, numeric = false) => {
    const active = sort.startsWith(`${column}-`), ascending = sort.endsWith('-asc');
    const next = `${column}-${active && ascending ? 'desc' : 'asc'}` as Sort;
    return <Table.Th className={numeric ? 'numeric' : undefined} aria-sort={active ? ascending ? 'ascending' : 'descending' : 'none'}>
      <button className="sort-button" onClick={() => onSort(next)}>{label}{active && <span aria-hidden="true"> {ascending ? '↑' : '↓'}</span>}</button>
    </Table.Th>;
  };
  const byTotal = sort.startsWith('total');
  return <div className="sheet-scroll"><Table className="price-sheet" aria-label="Drive prices" verticalSpacing="sm">
    <Table.Thead><Table.Tr><Table.Th>Drive</Table.Th>{heading('capacity', 'Capacity')}{heading('unit', '$/TB', true)}{heading('total', 'Total', true)}<Table.Th><span className="range-heading">Item price vs low, last
      <NativeSelect size="xs" aria-label="Days the range looks back over" value={String(rangeDays)} data={periods.map(days => ({ value: String(days), label: `${days} days` }))}
        onChange={event => onRangeDays(Number(event.currentTarget.value) as Period)} /></span></Table.Th>{heading('checked', 'Checked')}</Table.Tr></Table.Thead>
    <Table.Tbody>{groups.map(group => {
      const listing = group.offer, { latest } = listing;
      const age = now.getTime() - Date.parse(listing.last_checked_at);
      // One store can sell a drive in several conditions: the market counts stores, not offers.
      const { stores } = group;
      const others = marketChoices(group.conditions).filter(choice => choice.condition !== listing.condition);
      return <Table.Tr key={group.key} className="drive-row" onClick={() => onSelect(group.key, listing.condition)}>
        <Table.Td data-label="Drive"><button type="button" className="drive-link" title={listing.title}>{driveName(listing.drive)}
          {/* Names are not unique: the MPN is what tells two drives of the same name apart. */}
          <span className="secondary mono drive-mpn">{listing.mpn}</span></button>
          <div className="secondary">{sellerLabel(listing)}{stores > 1 && ` +${stores - 1} more`}</div>
          {others.length > 0 && <div className="also"><span className="secondary">Also</span>{others.map(choice =>
            <button key={choice.condition} type="button" className="also-condition"
              onClick={event => { event.stopPropagation(); onSelect(group.key, choice.condition); }}>{choice.label} <span className="mono">{priceLabel(choice)}</span></button>)}</div>}</Table.Td>
        <Table.Td data-label="Capacity" className="mono">{capacityLabel(listing.capacity_gb)}
          {listing.doubt && <div><span className="tag doubt" title={doubts[listing.doubt].why}>{doubts[listing.doubt].label}</span></div>}</Table.Td>
        {/* The price the list is ordered by leads; the other is said beside it, plainly. */}
        <Table.Td data-label="$/TB" className="numeric"><strong className={byTotal ? 'unit-price' : 'unit-price lead-price'}>{`$${latest.price_per_tb}`}</strong>
          {/* The condition sits under the price it belongs to. */}
          <div className="secondary">{conditionLabel(listing.condition)}</div>
          {leaders.unit.has(listing.id) && <div><span className="tag lowest" title={`Among offers in stock and checked within ${recentDays} days`}>Lowest $/TB</span></div>}</Table.Td>
        <Table.Td data-label="Total" className="numeric"><span className={byTotal ? 'total-price lead-price' : 'total-price'}>{dollars(latest.total_cents)}</span>
          {shippingLabel(latest) && <div className="secondary">{shippingLabel(latest)}</div>}
          {leaders.total.has(listing.id) && <div><span className="tag lowest" title={`Among offers in stock and checked within ${recentDays} days`}>Lowest total</span></div>}</Table.Td>
        <Table.Td data-label="Above low" className="range">{ranges[group.key] && <PriceRangeBar range={ranges[group.key]} days={rangeDays} />}</Table.Td>
        <Table.Td data-label="Checked" className="checked">
          <time dateTime={listing.last_checked_at} title={new Date(listing.last_checked_at).toLocaleString()}>{age < 0 ? 'Future date' : `${ageLabel(age)} ago`}</time>
          {!isRecent(listing, now, recentDays) && <div><span className="tag stale" title={`Not checked in ${recentDays} days`}>Stale</span></div>}
          {!latest.in_stock && <div><span className="tag">Out of stock</span></div>}</Table.Td>
      </Table.Tr>;
    })}</Table.Tbody>
  </Table></div>;
}
