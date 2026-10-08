export const specLabels = { media_type: 'Media type', form_factor: 'Form factor', interface: 'Interface', recording_type: 'Recording type', intended_use: 'Intended use' };
export type SpecKey = keyof typeof specLabels;
export type Specifications = { media_type: string; form_factor: string; interface: string; recording_type: string; intended_use: string[] };

const option = (value: string, label: string) => ({ value, label });
export const specOptions: Record<SpecKey, { value: string; label: string }[]> = {
  media_type: [option('unknown', 'Unknown'), option('hdd', 'Hard drive'), option('ssd', 'SSD'), option('flash_card', 'Flash card')],
  form_factor: [option('unknown', 'Unknown'), option('3_5', '3.5"'), option('2_5', '2.5"'), option('m_2', 'M.2'),
    option('microsd', 'microSD'), option('sd', 'SD')],
  interface: [option('unknown', 'Unknown'), option('sata', 'SATA'), option('sas', 'SAS'), option('nvme_pcie', 'NVMe/PCIe'), option('usb', 'USB')],
  recording_type: [option('unknown', 'Unknown'), option('cmr', 'CMR'), option('smr', 'SMR')],
  intended_use: [option('nas', 'NAS'), option('surveillance', 'Surveillance'), option('enterprise', 'Enterprise'),
    option('desktop', 'Desktop'), option('archive', 'Archive')],
};

export const emptySpecifications = (): Specifications => ({ media_type: 'unknown', form_factor: 'unknown', interface: 'unknown', recording_type: 'unknown', intended_use: [] });

const values = (specs: Specifications, key: SpecKey): string[] => {
  const value = specs[key];
  if (Array.isArray(value)) return value.length ? value : ['unknown'];
  return [value];
};

export const specLabel = (key: SpecKey, value: string) =>
  value === 'unknown' ? 'Unknown' : specOptions[key].find(option => option.value === value)?.label ?? value;

export function specificationLabel(key: SpecKey, specs: Specifications): string {
  return values(specs, key).map(value => specLabel(key, value)).join(', ');
}

export function matchesSpecification(specs: Specifications, key: SpecKey, value: string): boolean {
  return !value || values(specs, key).includes(value);
}
