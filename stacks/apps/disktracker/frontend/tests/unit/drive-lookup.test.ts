import { expect, it, vi } from 'vitest';
import { driveFor } from '../../src/drive-lookup';
import type { DisktrackerApi } from '../../src/api';
import { makeDrive, unusedWrites } from '../fixtures/listings';

const api = (findDrives: DisktrackerApi['findDrives']) => {
  const createDrive = vi.fn<DisktrackerApi['createDrive']>(async ({ mpn }) => makeDrive(mpn));
  return { api: { ...unusedWrites, findDrives, createDrive } as DisktrackerApi, createDrive };
};

it('makes a drive only when the lookup found none, not when it could not look', async () => {
  const none = api(async () => ({ items: [], total: 0, limit: 1, offset: 0 }));
  expect(await driveFor(none.api, 'ST18000NM000J', 18000)).toEqual({ drive: makeDrive('ST18000NM000J') });
  expect(none.createDrive).toHaveBeenCalledWith({ mpn: 'ST18000NM000J', capacity_gb: 18000 });

  const failing = api(async () => { throw new Error('Unable to save or load listings (503).'); });
  await expect(driveFor(failing.api, 'ST18000NM000J', 18000)).rejects.toThrow('Unable to save or load listings (503).');
  expect(failing.createDrive).not.toHaveBeenCalled();
});
