import type { TrendSplit } from './api';
import { readQuery, scopeSearch, type ListingQuery } from './listing-query';

/** The app's pages, told apart by path under the base it is served from (/, or a proxy prefix). */
export type View = 'listings' | 'trends' | 'admin';
/** The admin page's tabs: what waits on a person, the stores, the drives, and the rules that read
 * an offer's condition, which every store's offers are read by. */
export const adminTabs = ['todo', 'stores', 'drives', 'rules'] as const;
export type AdminTab = typeof adminTabs[number];

export function viewAt(pathname: string, base: string): View {
  const path = pathname.slice(base.length);
  return /^admin(\/|$)/.test(path) ? 'admin' : /^trends\/?$/.test(path) ? 'trends' : 'listings';
}

/** The tab an admin path names; To do for the page itself, and for anything unknown. */
export function adminTabAt(pathname: string, base: string): AdminTab {
  const named = /^admin\/([a-z]+)\/?$/.exec(pathname.slice(base.length))?.[1];
  return adminTabs.find(tab => tab === named) ?? 'todo';
}

export function pathFor(view: View, base: string, tab: AdminTab = 'todo'): string {
  if (view === 'listings') return base;
  if (view === 'trends') return `${base}trends`;
  return tab === 'todo' ? `${base}admin` : `${base}admin/${tab}`;
}

/** The days a trend can look back over. */
export const trendPeriods = [7, 14, 30, 90, 180] as const;
export type TrendPeriod = typeof trendPeriods[number];
/** What the trends page shows: how many days it looks back over (null: the longest there are prices
 * for), what it splits the market by, and which drives it follows, as the Prices filters narrow them. */
export type TrendQuery = { days: TrendPeriod | null; by: TrendSplit | null; scope: ListingQuery };
const splits: TrendSplit[] = ['condition', 'capacity', 'store'];

export function readTrendQuery(search: string): TrendQuery {
  const params = new URLSearchParams(search);
  return {
    days: trendPeriods.find(period => String(period) === params.get('days')) ?? null,
    by: splits.find(split => split === params.get('by')) ?? null,
    // Only what narrows which drives: anything else of the Prices page's is its own.
    scope: readQuery(scopeSearch(readQuery(search))),
  };
}

export function writeTrendQuery({ days, by, scope }: TrendQuery): string {
  const params = new URLSearchParams(scopeSearch(scope));
  if (by) params.set('by', by);
  if (days !== null) params.set('days', String(days));
  return params.toString();
}
