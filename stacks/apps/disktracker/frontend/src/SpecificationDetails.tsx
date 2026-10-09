import { Text } from '@mantine/core';
import { specLabels, specificationLabel, type SpecKey, type Specifications } from './specifications';

export function SpecificationDetails({ value }: { value: Specifications }) {
  return <section aria-label="Drive specifications"><dl className="spec-details">
    {(Object.keys(specLabels) as SpecKey[]).map(key =>
      <div key={key}><dt>{specLabels[key]}</dt><dd><Text size="sm">{specificationLabel(key, value)}</Text></dd></div>)}
  </dl></section>;
}
