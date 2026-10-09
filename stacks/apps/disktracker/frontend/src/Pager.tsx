import { Button, Group, NativeSelect, Text } from '@mantine/core';
import { PAGE_SIZES } from './paging';

type Props = {
  /** What is being paged, for its names: "Drives" gives "Drives pages" and "Drives rows per page". */
  label: string; page: number; total: number; pageSize: number;
  onPage: (page: number) => void; onPageSize: (size: number) => void;
};

/** Which rows of a long list are shown, the way to the rows before and after, and how many to
 * show at once. A list that fits on the smallest page has nothing to page through, so nothing
 * is shown. */
export function Pager({ label, page, total, pageSize, onPage, onPageSize }: Props) {
  if (total <= PAGE_SIZES[0]) return null;
  const first = page * pageSize + 1, last = Math.min(total, (page + 1) * pageSize);
  return <nav aria-label={`${label} pages`} className="pager"><Group gap="sm">
    <Button variant="default" disabled={page === 0} onClick={() => onPage(page - 1)}>Previous page</Button>
    <Text size="sm" className="pager-range">{`${first.toLocaleString()}–${last.toLocaleString()} of ${total.toLocaleString()}`}</Text>
    <Button variant="default" disabled={last >= total} onClick={() => onPage(page + 1)}>Next page</Button>
    <NativeSelect w={150} aria-label={`${label} rows per page`} value={String(pageSize)}
      data={PAGE_SIZES.map(size => ({ value: String(size), label: `${size} per page` }))}
      onChange={event => onPageSize(Number(event.currentTarget.value))} />
  </Group></nav>;
}
