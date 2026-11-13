import { useEffect, useState } from 'react';

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

/** A page of a list the server serves, as it last answered what was asked last: an answer that
 * comes after it, asked before, is dropped. The list starts again from its first page whenever
 * the filter or the page size changes, and a page left empty by rows going away gives way to the
 * last page there is, worked out from the total. Asked again whenever `revision` changes.
 * serve must keep its identity between renders (useCallback), or every render asks again. */
export function useServedPages<F, P extends { items: unknown[]; total: number }>(
  serve: (filter: F, limit: number, offset: number) => Promise<P>, filter: F,
  storage: Pick<Storage, 'getItem' | 'setItem'>, list: string, revision: number,
) {
  const [size, keepSize] = usePageSize(storage, list);
  const asked = JSON.stringify(filter);
  const within = `${size}\n${asked}`;
  const [at, setAt] = useState({ page: 0, within, attempt: 0 });
  const page = at.within === within ? at.page : 0;
  /** The last answer, with the page it is. */
  const [shown, setShown] = useState<{ page: number; found: P } | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let current = true;
    serve(JSON.parse(asked) as F, size, page * size).then(found => {
      if (!current) return;
      const last = Math.max(0, Math.ceil(found.total / size) - 1);
      if (!found.items.length && last < page) { setAt({ page: last, within, attempt: at.attempt }); return; }
      setShown({ page, found }); setError('');
    }).catch(err => { if (current) setError(err instanceof Error ? err.message : 'Unknown error.'); });
    return () => { current = false; };
  }, [serve, asked, size, page, revision, at.attempt]);
  return {
    found: shown?.found ?? null, page: shown?.page ?? 0, size, error,
    setPage: (next: number) => setAt({ page: next, within, attempt: at.attempt }),
    setSize: keepSize,
    retry: () => setAt({ page, within, attempt: at.attempt + 1 }),
  };
}
