import { expect, it } from 'vitest';
import { adminTabAt, pathFor, viewAt } from '../../src/view';

it.each([
  ['/', '/', 'listings'], ['/admin', '/', 'admin'], ['/admin/', '/', 'admin'], ['/admin/stores', '/', 'admin'],
  ['/absproxy/5173/', '/absproxy/5173/', 'listings'], ['/absproxy/5173/admin', '/absproxy/5173/', 'admin'],
  ['/absproxy/5173/admin/drives', '/absproxy/5173/', 'admin'], ['/administrator', '/', 'listings'],
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
});
