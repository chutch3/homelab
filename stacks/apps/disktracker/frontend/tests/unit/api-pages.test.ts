import { expect, it } from 'vitest';
import { HttpListingsApi } from '../../src/api';
import { makeUnmatched } from '../fixtures/listings';

it('asks for one page of the review queue and reads how many offers there are in all', async () => {
  const asked: string[] = [];
  const api = new HttpListingsApi(async url => {
    asked.push(String(url));
    return new Response(JSON.stringify([makeUnmatched('a'), makeUnmatched('b')]), { headers: { 'X-Total-Count': '1709' } });
  }, '/api');

  const page = await api.listUnmatched({ limit: 50, offset: 100 });

  expect(asked).toEqual(['/api/unmatched?limit=50&offset=100']);
  expect(page.items.map(item => item.id)).toEqual(['a', 'b']);
  expect(page.total).toBe(1709);
});

it('says so when a page cannot be loaded', async () => {
  const api = new HttpListingsApi(async () => new Response('', { status: 503 }), '/api');
  await expect(api.listUnmatched({ limit: 50, offset: 0 })).rejects.toThrow('Unable to save or load listings (503).');
});
