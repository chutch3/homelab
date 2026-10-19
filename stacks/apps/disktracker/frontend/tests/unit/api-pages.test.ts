import { expect, it } from 'vitest';
import { HttpDisktrackerApi } from '../../src/api';
import { makeReviewItem } from '../fixtures/listings';

it('asks for one page of the review queue and reads how many offers there are in all', async () => {
  const asked: string[] = [];
  const api = new HttpDisktrackerApi(async url => {
    asked.push(String(url));
    return new Response(JSON.stringify([makeReviewItem('a'), makeReviewItem('b')]), { headers: { 'X-Total-Count': '1709' } });
  }, '/api');

  const page = await api.reviewItems({ limit: 50, offset: 100 });

  expect(asked).toEqual(['/api/review-items?limit=50&offset=100']);
  expect(page.items.map(item => item.id)).toEqual(['a', 'b']);
  expect(page.total).toBe(1709);
});

it('says so when a page cannot be loaded', async () => {
  const api = new HttpDisktrackerApi(async () => new Response('', { status: 503 }), '/api');
  await expect(api.reviewItems({ limit: 50, offset: 0 })).rejects.toThrow('Unable to save or load listings (503).');
});

it('asks for trends over a period, split when a split is chosen, saying how long an offer may go unchecked', async () => {
  const asked: string[] = [];
  const answer = { days: 30, by: 'capacity', market: { counted: 0, of: 0, points: [] }, parts: [], since: null };
  const api = new HttpDisktrackerApi(async url => { asked.push(String(url)); return new Response(JSON.stringify(answer)); }, '/api');

  expect(await api.trends(30, 'capacity', 7, {})).toEqual(answer);
  await api.trends(90, null, 14, {});
  // Narrowed to some drives, each choice of a filter repeated.
  await api.trends(7, null, 7, { q: 'exos', capacity: [18000, 20000] });

  expect(asked).toEqual(['/api/trends?days=30&recent_days=7&by=capacity', '/api/trends?days=90&recent_days=14',
    '/api/trends?days=7&recent_days=7&q=exos&capacity=18000&capacity=20000']);
});

it('asks for the collector runs that ended since a moment, and the latest run of each store', async () => {
  const asked: string[] = [];
  const api = new HttpDisktrackerApi(async url => { asked.push(String(url)); return new Response('[]'); }, '/api');
  expect(await api.recentRuns('2026-09-21T12:00:00.000Z')).toEqual([]);
  expect(await api.latestRuns()).toEqual([]);
  expect(asked).toEqual(['/api/collection-runs?finished_since=2026-09-21T12%3A00%3A00.000Z', '/api/collection-runs?latest_per_source=true']);
});

it('reads and changes offers, prices, drives and review items at their own addresses', async () => {
  const sent: string[] = [];
  const api = new HttpDisktrackerApi(async (url, init) => {
    sent.push(`${init?.method} ${String(url)}${init?.body ? ` ${String(init.body)}` : ''}`);
    return init?.method === 'DELETE' ? new Response(null, { status: 204 }) : new Response('[]');
  }, '/api');

  await api.listOffers();
  await api.editOffer('a', { title: 'Exos X18', url: null });
  await api.deleteOffer('a');
  expect(await api.deletePrice('p')).toBeNull();
  await api.editDrive('d', { capacity_gb: 18000 });
  await api.decide('r', { decision: 'match', mpn: 'ST18000NM000J', condition: 'new', capacity_gb: 18000 });
  await api.decide('r', { decision: 'ignore' });

  expect(sent).toEqual([
    'GET /api/offers',
    'PATCH /api/offers/a {"title":"Exos X18","url":null}',
    'DELETE /api/offers/a',
    'DELETE /api/prices/p',
    'PATCH /api/drives/d {"capacity_gb":18000}',
    'PUT /api/review-items/r/decision {"decision":"match","mpn":"ST18000NM000J","condition":"new","capacity_gb":18000}',
    'PUT /api/review-items/r/decision {"decision":"ignore"}',
  ]);
});

it('asks the server for a page of drives with every filter as a query parameter', async () => {
  const asked: string[] = [];
  const page = { items: [], total: 0, offers: 0, sold_out: 0, limit: 25, offset: 50, as_of: '2026-09-22T12:00:00Z',
    lowest: { total: [], unit: [] }, filter_options: { brands: [], capacities: [], conditions: [] } };
  const api = new HttpDisktrackerApi(async url => { asked.push(String(url)); return new Response(JSON.stringify(page)); }, '/api');

  expect(await api.drives({
    q: 'exos x18', brand: ['Seagate', 'unknown'], capacity: [18000], condition: ['new'], store: ['goharddrive'],
    max_total_cents: 20000, interface: 'sata', intended_use: 'nas', in_stock: false, recent_only: true,
    recent_days: 7, sort: 'total-desc', range_days: 30, limit: 25, offset: 50,
  })).toEqual(page);
  await api.drives({ recent_days: 7, sort: 'unit-asc', range_days: 90, limit: 50, offset: 0 });
  await api.drives({ drive_id: 'd', recent_days: 7, sort: 'unit-asc', range_days: 90, limit: 1, offset: 0 });

  expect(asked).toEqual([
    '/api/drives?q=exos+x18&brand=Seagate&brand=unknown&capacity=18000&condition=new&store=goharddrive&max_total_cents=20000'
      + '&interface=sata&intended_use=nas&in_stock=false&recent_only=true&recent_days=7&sort=total-desc&range_days=30&limit=25&offset=50',
    '/api/drives?recent_days=7&sort=unit-asc&range_days=90&limit=50&offset=0',
    '/api/drives?drive_id=d&recent_days=7&sort=unit-asc&range_days=90&limit=1&offset=0',
  ]);
});

it('asks the server for a page of the drives to manage by words and need, leaving out what is not asked', async () => {
  const asked: string[] = [];
  const page = { items: [], total: 0, all: 0, issues: { unknown_specifications: 0, stale: 0 }, limit: 25, offset: 25 };
  const api = new HttpDisktrackerApi(async url => { asked.push(String(url)); return new Response(JSON.stringify(page)); }, '/api');

  expect(await api.catalogDrives({ q: 'wuh 72', issue: 'stale', recent_days: 14, limit: 25, offset: 25 })).toEqual(page);
  await api.catalogDrives({ q: '', recent_days: 7, limit: 50, offset: 0 });

  expect(asked).toEqual([
    '/api/catalog-drives?q=wuh+72&issue=stale&recent_days=14&limit=25&offset=25',
    '/api/catalog-drives?recent_days=7&limit=50&offset=0',
  ]);
});

it('reads a drive, its prices a page at a time, the offers due a check, and what drives cost today', async () => {
  const asked: string[] = [];
  const api = new HttpDisktrackerApi(async url => {
    asked.push(String(url));
    const path = String(url);
    if (path.startsWith('/api/prices')) return new Response(JSON.stringify({ items: [], total: 0, limit: 500, offset: 0 }));
    return new Response(path.startsWith('/api/drives/') ? '{"drive":null,"offers":[]}' : '[]');
  }, '/api');

  await api.drive('d', 30, 7);
  await api.offer('o');
  await api.prices({ driveId: 'd' });
  await api.prices({ offerId: 'o', since: '2026-06-24T12:00:00Z', limit: 100, offset: 200 });
  await api.offersToRecheck(7);
  await api.pricesToday(14, {});

  expect(asked).toEqual([
    '/api/drives/d?range_days=30&recent_days=7',
    '/api/offers/o',
    '/api/prices?drive_id=d&limit=500&offset=0',
    '/api/prices?offer_id=o&since=2026-06-24T12%3A00%3A00Z&limit=100&offset=200',
    '/api/offers?needs_recheck=true&recent_days=7',
    '/api/reports/prices-today?recent_days=14',
  ]);
});
