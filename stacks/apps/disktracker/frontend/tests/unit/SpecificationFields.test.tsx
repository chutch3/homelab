import { useState } from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { SpecificationFields } from '../../src/SpecificationFields';
import { emptySpecifications, type Specifications } from '../../src/specifications';

afterEach(cleanup);

it('edits plain values with selects and intended-use checkboxes, and nothing else', async () => {
  let latest: Specifications = emptySpecifications();
  function Form() {
    const [value, setValue] = useState(emptySpecifications);
    return <SpecificationFields value={value} onChange={next => { latest = next; setValue(next); }} />;
  }
  render(<MantineProvider env="test"><Form /></MantineProvider>);
  const user = userEvent.setup();
  expect(within(screen.getByLabelText('Media type', { exact: true })).getAllByRole('option').map(option => option.textContent))
    .toEqual(['Unknown', 'Hard drive', 'SSD', 'Flash card']);
  expect(within(screen.getByLabelText('Form factor', { exact: true })).getAllByRole('option').map(option => option.textContent))
    .toEqual(['Unknown', '3.5"', '2.5"', 'M.2', 'microSD', 'SD']);
  expect(within(screen.getByLabelText('Interface', { exact: true })).getAllByRole('option').map(option => option.textContent))
    .toEqual(['Unknown', 'SATA', 'SAS', 'NVMe/PCIe', 'USB']);
  expect(screen.queryAllByLabelText(/source|verification|SMR management|Other/i)).toHaveLength(0);
  await user.selectOptions(screen.getByLabelText('Media type', { exact: true }), 'ssd');
  await user.selectOptions(screen.getByLabelText('Form factor', { exact: true }), '2_5');
  await user.selectOptions(screen.getByLabelText('Interface', { exact: true }), 'sas');
  await user.selectOptions(screen.getByLabelText('Recording type', { exact: true }), 'smr');
  await user.click(screen.getByLabelText('NAS', { exact: true }));
  await user.click(screen.getByLabelText('Archive', { exact: true }));
  expect(latest).toEqual({
    media_type: 'ssd', form_factor: '2_5', interface: 'sas', recording_type: 'smr', intended_use: ['nas', 'archive'],
  });
});
