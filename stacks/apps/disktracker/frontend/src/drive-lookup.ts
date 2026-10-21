import type { DisktrackerApi, Drive } from './api';

/** Whether a drive goes by this MPN, as its own or another of its MPNs, in any case. */
export const goesBy = (drive: Drive, mpn: string) => [drive.mpn, ...drive.aliases].some(name => name.toUpperCase() === mpn.toUpperCase());

/** The drive the server finds recorded under an MPN, if any is; none when it cannot say. */
export const findDrive = (api: DisktrackerApi, mpn: string): Promise<Drive | undefined> =>
  api.catalogDrives({ q: mpn, limit: 8, offset: 0 })
    .then(page => page.items.find(row => goesBy(row.drive, mpn))?.drive)
    .catch(() => undefined);

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
