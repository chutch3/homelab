import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { unusedWrites, makeDrive } from '../fixtures/listings';
import { emptySpecifications } from '../../src/specifications';
import { DriveForm } from '../../src/DriveForm';
import { ApiValidationError, type Drive, type ListingsApi } from '../../src/api';

afterEach(cleanup);

it('saves the capacity and plain specifications for every listing sharing the drive', async () => {
  const user = userEvent.setup();
  const drive = makeDrive('ST18000NM000J');
  const saved: Drive = { ...drive, specifications: { ...emptySpecifications(), interface: 'sata' } };
  const replaceSpecifications = vi.fn<ListingsApi['replaceSpecifications']>(async () => saved);
  const onSaved = vi.fn();
  render(<MantineProvider env="test"><DriveForm drive={drive} api={{ ...unusedWrites, replaceSpecifications }}
    onClose={() => {}} onSaved={onSaved} /></MantineProvider>);
  const form = within(screen.getByRole('dialog', { name: 'Edit specifications' }));
  expect(form.queryByLabelText('Reason')).not.toBeInTheDocument();
  expect(form.getByLabelText('Capacity', { exact: true })).toHaveValue('18000');
  await user.selectOptions(form.getByLabelText('Interface', { exact: true }), 'sata');
  await user.click(form.getByRole('button', { name: 'Save' }));
  await waitFor(() => expect(replaceSpecifications).toHaveBeenCalledWith(drive.id, { capacity_gb: 18000, specifications: saved.specifications, brand: '' }));
  expect(onSaved).toHaveBeenCalledWith(saved);
});

it("corrects the drive's brand, which the collector then leaves alone", async () => {
  const user = userEvent.setup();
  const drive = { ...makeDrive('ST18000NM000J'), brand: 'Dell' };
  const replaceSpecifications = vi.fn<ListingsApi['replaceSpecifications']>(async (_id, input) => ({ ...drive, brand: input.brand || null }));
  render(<MantineProvider env="test"><DriveForm drive={drive} api={{ ...unusedWrites, replaceSpecifications }}
    onClose={() => {}} onSaved={() => {}} /></MantineProvider>);
  const form = within(screen.getByRole('dialog', { name: 'Edit specifications' }));
  const brand = form.getByLabelText('Brand', { exact: true });
  expect(brand).toHaveValue('Dell');
  await user.clear(brand);
  await user.type(brand, ' Seagate ');
  await user.click(form.getByRole('button', { name: 'Save' }));
  await waitFor(() => expect(replaceSpecifications).toHaveBeenCalledWith(drive.id, expect.objectContaining({ brand: 'Seagate' })));
});

it('shows a rejected capacity on the capacity field without closing', async () => {
  const user = userEvent.setup();
  const drive = makeDrive('ST18000NM000J');
  const replaceSpecifications = vi.fn(async (): Promise<Drive> => {
    throw new ApiValidationError({ capacity_gb: 'Capacity was rejected.' });
  });
  const onClose = vi.fn();
  render(<MantineProvider env="test"><DriveForm drive={drive} api={{ ...unusedWrites, replaceSpecifications }}
    onClose={onClose} onSaved={() => {}} /></MantineProvider>);
  await user.click(screen.getByRole('button', { name: 'Save' }));
  expect(await screen.findByLabelText('Capacity', { exact: true })).toHaveAccessibleDescription('Capacity was rejected.');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(onClose).not.toHaveBeenCalled();
});

it('shows a rejection it cannot place on a field as an alert', async () => {
  const user = userEvent.setup();
  const replaceSpecifications = vi.fn(async (): Promise<Drive> => {
    throw new ApiValidationError({ 'specifications.interface': 'Input should be sata, sas or nvme.' });
  });
  render(<MantineProvider env="test"><DriveForm drive={makeDrive('ST18000NM000J')} api={{ ...unusedWrites, replaceSpecifications }}
    onClose={() => {}} onSaved={() => {}} /></MantineProvider>);
  await user.click(screen.getByRole('button', { name: 'Save' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Check the submitted entry.');
});

it('keeps an unusual recorded capacity under Other', () => {
  const drive = makeDrive('X5', { capacity_gb: 5500 });
  render(<MantineProvider env="test"><DriveForm drive={drive} api={unusedWrites}
    onClose={() => {}} onSaved={() => {}} /></MantineProvider>);
  expect(screen.getByLabelText('Capacity', { exact: true })).toHaveValue('other');
  expect(screen.getByLabelText('Other capacity (GB)', { exact: true })).toHaveValue(5500);
});

it('adds another MPN for the drive and lists its aliases', async () => {
  const user = userEvent.setup();
  const drive = makeDrive('ST18000NM000J', { aliases: ['ST18000NM000J-0001'] });
  const addAlias = vi.fn<ListingsApi['addAlias']>(async (_id, mpn) => ({ ...drive, aliases: ['ST18000NM000J-0001', mpn.toUpperCase()] }));
  const onAliasAdded = vi.fn(async () => {});
  render(<MantineProvider env="test"><DriveForm drive={drive} api={{ ...unusedWrites, addAlias }}
    onClose={() => {}} onSaved={() => {}} onAliasAdded={onAliasAdded} /></MantineProvider>);
  const form = within(screen.getByRole('dialog', { name: 'Edit specifications' }));
  expect(form.getByText('ST18000NM000J-0001')).toBeVisible();
  await user.type(form.getByRole('textbox', { name: 'Other MPN' }), 'st18000nm000j-2e3101');
  await user.click(form.getByRole('button', { name: 'Add MPN' }));
  expect(addAlias).toHaveBeenCalledWith(drive.id, 'st18000nm000j-2e3101');
  expect(await form.findByText('ST18000NM000J-2E3101')).toBeVisible();
  expect(onAliasAdded).toHaveBeenCalled();
});

it('explains why an MPN could not be added', async () => {
  const user = userEvent.setup();
  const drive = makeDrive('ST18000NM000J');
  const addAlias = vi.fn(async (): Promise<Drive> => { throw new Error('ST18000NM000J already identifies a drive.'); });
  render(<MantineProvider env="test"><DriveForm drive={drive} api={{ ...unusedWrites, addAlias }}
    onClose={() => {}} onSaved={() => {}} onAliasAdded={async () => {}} /></MantineProvider>);
  const form = within(screen.getByRole('dialog', { name: 'Edit specifications' }));
  await user.type(form.getByRole('textbox', { name: 'Other MPN' }), 'ST18000NM000J');
  await user.click(form.getByRole('button', { name: 'Add MPN' }));
  expect(await form.findByText('ST18000NM000J already identifies a drive.')).toBeVisible();
});
