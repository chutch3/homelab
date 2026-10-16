import { defaultQuery } from '../../src/listing-query';
import { expect, it } from 'vitest';
import { adminTabAt, pathFor, readTrendQuery, viewAt, writeTrendQuery } from '../../src/view';

it.each([
  ['/', '/', 'listings'], ['/admin', '/', 'admin'], ['/admin/', '/', 'admin'], ['/admin/stores', '/', 'admin'],
  ['/absproxy/5173/', '/absproxy/5173/', 'listings'], ['/absproxy/5173/admin', '/absproxy/5173/', 'admin'],
  ['/absproxy/5173/admin/drives', '/absproxy/5173/', 'admin'], ['/administrator', '/', 'listings'],
  ['/trends', '/', 'trends'], ['/trends/', '/', 'trends'], ['/absproxy/5173/trends', '/absproxy/5173/', 'trends'], ['/trendsetter', '/', 'listings'],
] as const)('reads %s under base %s as the %s page', (pathname, base, view) => {
  expect(viewAt(pathname, base)).toBe(view);
});

it.each([
  ['/admin', '/', 'todo'], ['/admin/', '/', 'todo'], ['/admin/stores', '/', 'stores'], ['/admin/drives/', '/', 'drives'],
  ['/absproxy/5173/admin/stores', '/absproxy/5173/', 'stores'], ['/admin/elsewhere', '/', 'todo'], ['/', '/', 'todo'],
] as const)('reads %s under base %s as the admin page\'s %s tab', (pathname, base, tab) => {
  expect(adminTabAt(pathname, base)).toBe(tab);
});

it('builds each page path under the base the app is served from', () => {
  expect(pathFor('admin', '/absproxy/5173/')).toBe('/absproxy/5173/admin');
  expect(pathFor('admin', '/absproxy/5173/', 'todo')).toBe('/absproxy/5173/admin');
  expect(pathFor('admin', '/absproxy/5173/', 'stores')).toBe('/absproxy/5173/admin/stores');
  expect(pathFor('listings', '/absproxy/5173/')).toBe('/absproxy/5173/');
  expect(pathFor('trends', '/absproxy/5173/')).toBe('/absproxy/5173/trends');
});

it('reads the period, split and drives of the trends page from its URL, and writes only what was chosen', () => {
  const every = defaultQuery();
  // No period chosen: the page picks one.
  expect(readTrendQuery('')).toEqual({ days: null, by: null, scope: every });
  expect(readTrendQuery('?by=store&days=180')).toEqual({ days: 180, by: 'store', scope: every });
  expect(readTrendQuery('?by=brand&days=45')).toEqual({ days: null, by: null, scope: every });
  // Only what narrows which drives: the Prices page's order and stock are its own.
  expect(readTrendQuery('?q=exos&capacity=18000&sort=total-asc&stock=all').scope).toEqual({ ...every, search: 'exos', capacities: ['18000'] });
  expect(writeTrendQuery({ days: null, by: null, scope: every })).toBe('');
  expect(writeTrendQuery({ days: 30, by: 'capacity', scope: every })).toBe('by=capacity&days=30');
  expect(writeTrendQuery({ days: 7, by: null, scope: { ...every, search: 'exos', capacities: ['18000'] } })).toBe('q=exos&capacity=18000&days=7');
});
