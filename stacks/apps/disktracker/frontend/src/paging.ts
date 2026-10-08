import { useState } from 'react';

/** The numbers of rows a long list can show at once, and the number it shows until one is chosen. */
export const PAGE_SIZES = [25, 50, 100, 200];
export const PAGE_SIZE = 50;

/** How many rows a list shows at once: chosen for each list apart, and kept between visits. */
export function usePageSize(storage: Pick<Storage, 'getItem' | 'setItem'>, list: string): [number, (size: number) => void] {
  const key = `disktracker.page-size.${list}`;
  const [size, setSize] = useState(() => {
    const kept = Number(storage.getItem(key));
    return PAGE_SIZES.includes(kept) ? kept : PAGE_SIZE;
  });
  return [size, next => { storage.setItem(key, String(next)); setSize(next); }];
}

/** One page of a list held in full: its rows, and the page it is. The list starts again from
 * its first page whenever `within` changes (a search, a filter, an order) or the page size
 * does, and a page left empty by rows going away falls back to the last one there is. */
export function usePages<T>(rows: T[], pageSize: number, within = '') {
  const scope = `${pageSize}\n${within}`;
  const [at, setAt] = useState({ page: 0, scope });
  const last = Math.max(0, Math.ceil(rows.length / pageSize) - 1);
  const page = at.scope === scope ? Math.min(at.page, last) : 0;
  return {
    page, shown: rows.slice(page * pageSize, (page + 1) * pageSize),
    setPage: (next: number) => setAt({ page: next, scope }),
  };
}
