import { expect, it } from 'vitest';
import { asksForSeller, capacityLabel, driveName, sellerLabel } from '../../src/listing-display';
import { makeDrive } from '../fixtures/listings';
import { emptySpecifications } from '../../src/specifications';

it('names an offer by its store', () => {
  expect(sellerLabel({ store: 'serverorbit', store_name: 'ServerOrbit', seller: '' })).toBe('ServerOrbit');
});

it('names an Other offer by its store name alone', () => {
  expect(sellerLabel({ store: 'other', store_name: 'Other', seller: 'Micro Center' })).toBe('Micro Center');
});

it('asks for a store name only for Other', () => {
  expect(['serverpartdeals', 'serverorbit', 'other'].filter(asksForSeller)).toEqual(['other']);
});

it.each([[18000, '18 TB'], [1920, '1.92 TB'], [1000, '1 TB'], [960, '960 GB'], [32, '32 GB']])(
  'labels %i GB as %s, switching to TB from one terabyte up', (gigabytes, label) => {
    expect(capacityLabel(gigabytes)).toBe(label);
  });

it('names a drive by what is recorded of it, the same wherever it is shown', () => {
  const specs = emptySpecifications();
  expect(driveName(makeDrive('ST18000NM000J', { brand: 'Seagate', specifications: { ...specs, media_type: 'hdd', interface: 'sata' } })))
    .toBe('Seagate 18 TB SATA hard drive');
  expect(driveName(makeDrive('MZ7L33T8HBLT', { brand: 'Samsung', capacity_gb: 3840, specifications: { ...specs, media_type: 'ssd', interface: 'nvme_pcie' } })))
    .toBe('Samsung 3.84 TB NVMe SSD');
  expect(driveName(makeDrive('SDSQXAV-128G', { brand: 'SanDisk', capacity_gb: 128, specifications: { ...specs, media_type: 'flash_card', form_factor: 'microsd' } })))
    .toBe('SanDisk 128 GB microSD card');
  // Nothing known but its capacity.
  expect(driveName(makeDrive('X1'))).toBe('18 TB drive');
});
