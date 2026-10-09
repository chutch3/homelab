import { useState } from 'react';
import { NativeSelect, TextInput } from '@mantine/core';
import { capacityLabel } from './listing-display';

// Whole decimal gigabytes: cards and small SSDs, then drive sizes from 1 TB.
const standardCapacities = [32, 64, 128, 256, 512, 1000, 2000, 3000, 4000, 6000, 8000, 10000, 12000, 14000, 16000,
  18000, 20000, 22000, 24000, 26000, 28000, 30000, 32000].map(String);
const options = [{ value: '', label: 'Choose capacity' },
  ...standardCapacities.map(value => ({ value, label: capacityLabel(Number(value)) })), { value: 'other', label: 'Other' }];

type Props = { value: string; onChange: (capacity: string) => void; error?: React.ReactNode };

export function CapacityField({ value, onChange, error }: Props) {
  const [choice, setChoice] = useState(() => {
    if (value === '') return '';
    return standardCapacities.includes(value) ? value : 'other';
  });
  return <>
    <NativeSelect label="Capacity" aria-label="Capacity" required data={options} value={choice}
      data-path={choice === 'other' ? undefined : 'capacity'} error={choice === 'other' ? undefined : error}
      onChange={event => {
        const next = event.currentTarget.value;
        setChoice(next);
        onChange(next === 'other' ? '' : next);
      }} />
    {choice === 'other' && <TextInput label="Other capacity (GB)" aria-label="Other capacity (GB)" type="number" required
      min="1" step="1" data-path="capacity" value={value} error={error}
      onChange={event => onChange(event.currentTarget.value)} />}
  </>;
}
