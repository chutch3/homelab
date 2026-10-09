import { Alert, Anchor, Text } from '@mantine/core';
import type { SourcePreview } from './api';
import { capacityLabel, conditionLabel, dollars } from './listing-display';

const reviewReasons: Record<string, string> = {
  missing_mpn: 'no MPN was read',
  missing_condition: 'no condition was read',
  missing_capacity: 'no capacity was read, and the drive is not known yet',
  capacity_conflict: 'its capacity differs from the one recorded for this drive',
};
/** What disktracker would do with the offer, in a sentence. */
function verdictLabel({ outcome, reason }: NonNullable<SourcePreview['verdict']>): string {
  if (outcome === 'recorded') return 'It would be recorded.';
  if (outcome === 'ignored') return 'It is sold out, so nothing would be recorded until it is in stock.';
  return `It would wait under Needs matching: ${reviewReasons[reason ?? ''] ?? reason}.`;
}
const unread = '—';

/** One offer as the collector read it from the source being tested, or why there is none. Nothing was saved. */
type Props = {
  preview: SourcePreview;
  /** What the result is of, and what its offer and notes are, where it is not a test of a store. */
  label?: string; lead?: string; notesLabel?: string;
  /** What is worth knowing about the store itself, where that was worked out. */
  store?: { label: string; value: string }[];
};

export function SourcePreviewResult({ preview, label = 'Test result', lead = 'The first offer read. Nothing was saved.', notesLabel = 'What was read', store = [] }: Props) {
  const { status, reason, offer, verdict, notes } = preview;
  return <section aria-label={label} className="source-preview">
    {status === 'failed' && <Alert color="red">The store could not be read: {reason}</Alert>}
    {status === 'nothing' && <Alert color="yellow">The store was read, but no drive was found.</Alert>}
    {offer && <>
      <Text size="sm" c="dimmed">{lead}</Text>
      <Anchor href={offer.url} target="_blank" rel="noreferrer">{offer.title}</Anchor>
      <dl className="source-preview-facts">
        {([
          ['MPN', offer.mpn ?? unread], ['Brand', offer.brand ?? unread],
          ['Condition', offer.condition ? conditionLabel(offer.condition) : unread],
          ['Capacity', offer.capacity_gb === null ? unread : capacityLabel(offer.capacity_gb)],
          ['Price', offer.item_price_cents === null ? unread : dollars(offer.item_price_cents)],
          ['Shipping', offer.shipping_cents === null ? 'Not known' : offer.shipping_cents === 0 ? 'Free' : dollars(offer.shipping_cents)],
          ['Stock', offer.in_stock ? 'In stock' : 'Out of stock'],
        ] as const).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>
      {verdict && <Alert color={verdict.outcome === 'recorded' ? 'green' : 'yellow'}>{verdictLabel(verdict)}</Alert>}
    </>}
    {store.length > 0 && <div role="group" aria-label="About the store">
      <Text size="sm" c="dimmed">About the store</Text>
      <dl className="source-preview-facts">{store.map(fact => <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}</dl>
    </div>}
    {notes.length > 0 && <>
      <Text size="sm" c="dimmed">{notesLabel}</Text>
      <ul className="source-preview-notes">{notes.map((note, index) => <li key={index}>{note}</li>)}</ul>
    </>}
  </section>;
}
