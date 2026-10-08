import { Checkbox, Group, NativeSelect, Stack } from '@mantine/core';
import { specLabels, specOptions, type Specifications } from './specifications';

type Props = { value: Specifications; onChange: (value: Specifications) => void };

export function SpecificationFields({ value, onChange }: Props) {
  return <Stack gap="md">
    <NativeSelect label={specLabels.media_type} aria-label={specLabels.media_type} data={specOptions.media_type}
      value={value.media_type} onChange={event => onChange({ ...value, media_type: event.currentTarget.value })} />
    <NativeSelect label={specLabels.form_factor} aria-label={specLabels.form_factor} data={specOptions.form_factor}
      value={value.form_factor} onChange={event => onChange({ ...value, form_factor: event.currentTarget.value })} />
    <NativeSelect label={specLabels.interface} aria-label={specLabels.interface} data={specOptions.interface}
      value={value.interface} onChange={event => onChange({ ...value, interface: event.currentTarget.value })} />
    <NativeSelect label={specLabels.recording_type} aria-label={specLabels.recording_type} data={specOptions.recording_type}
      value={value.recording_type} onChange={event => onChange({ ...value, recording_type: event.currentTarget.value })} />
    <Checkbox.Group label={specLabels.intended_use} value={value.intended_use}
      onChange={intended_use => onChange({ ...value, intended_use })}>
      <Group gap="sm" mt="xs">{specOptions.intended_use.map(option =>
        <Checkbox key={option.value} value={option.value} label={option.label} aria-label={option.label} />)}</Group>
    </Checkbox.Group>
  </Stack>;
}
