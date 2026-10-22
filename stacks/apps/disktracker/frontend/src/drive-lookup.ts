import type { DisktrackerApi, Drive } from './api';

/** The drive the server finds going by an MPN, as its own or another of its MPNs; none when none
 * does. A lookup that fails is a failure, never taken to mean there is none. */
export const findDrive = (api: DisktrackerApi, mpn: string): Promise<Drive | undefined> =>
  api.findDrives({ mpn, limit: 1, offset: 0 }).then(page => page.items[0]?.drive);

/** The drive something new is said of, before anything is said of it: the one already known, else the one found
 * recorded under its MPN now, else one made under it with the capacity given. A drive found at a capacity other than
 * the one given is not taken: a price or a decision never changes what a drive is. */
export async function driveFor(api: DisktrackerApi, mpn: string, capacityGb: number | null, known?: Drive):
  Promise<{ drive: Drive } | { recordedAs: Drive }> {
  const found = known ?? await findDrive(api, mpn);
  if (!found) return { drive: await api.createDrive({ mpn, capacity_gb: capacityGb ?? 0 }) };
  if (!known && capacityGb !== null && capacityGb !== found.capacity_gb) return { recordedAs: found };
  return { drive: found };
}
