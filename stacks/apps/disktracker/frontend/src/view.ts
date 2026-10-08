/** The app's two pages, told apart by path under the base it is served from (/, or a proxy prefix). */
export type View = 'listings' | 'admin';
/** The admin page's tabs: what waits on a person, the stores, and the drives. */
export const adminTabs = ['todo', 'stores', 'drives'] as const;
export type AdminTab = typeof adminTabs[number];

export function viewAt(pathname: string, base: string): View {
  return /^admin(\/|$)/.test(pathname.slice(base.length)) ? 'admin' : 'listings';
}

/** The tab an admin path names; To do for the page itself, and for anything unknown. */
export function adminTabAt(pathname: string, base: string): AdminTab {
  const named = /^admin\/([a-z]+)\/?$/.exec(pathname.slice(base.length))?.[1];
  return adminTabs.find(tab => tab === named) ?? 'todo';
}

export function pathFor(view: View, base: string, tab: AdminTab = 'todo'): string {
  if (view === 'listings') return base;
  return tab === 'todo' ? `${base}admin` : `${base}admin/${tab}`;
}
