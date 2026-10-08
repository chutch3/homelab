import { describe, expect, it } from 'vitest';
import { emptySpecifications, matchesSpecification, specificationLabel } from '../../src/specifications';

describe('specification labels', () => {
  it('shows each value by name and anything not entered as Unknown', () => {
    const specs = { ...emptySpecifications(), interface: 'sata', intended_use: ['nas', 'enterprise'] };
    expect(specificationLabel('interface', specs)).toBe('SATA');
    expect(specificationLabel('recording_type', specs)).toBe('Unknown');
    expect(specificationLabel('intended_use', specs)).toBe('NAS, Enterprise');
    expect(specificationLabel('intended_use', emptySpecifications())).toBe('Unknown');
  });
});

describe('specification matching', () => {
  const specs = { ...emptySpecifications(), interface: 'sata', recording_type: 'cmr', intended_use: ['nas', 'enterprise'] };
  it('matches the entered value, or any of several intended uses', () => {
    expect(matchesSpecification(specs, 'recording_type', 'cmr')).toBe(true);
    expect(matchesSpecification(specs, 'recording_type', 'smr')).toBe(false);
    expect(matchesSpecification(specs, 'intended_use', 'nas')).toBe(true);
    expect(matchesSpecification(specs, 'intended_use', 'surveillance')).toBe(false);
    expect(matchesSpecification(specs, 'interface', '')).toBe(true);
  });
  it('matches Unknown for values that were never entered', () => {
    expect(matchesSpecification(emptySpecifications(), 'interface', 'unknown')).toBe(true);
    expect(matchesSpecification(emptySpecifications(), 'intended_use', 'unknown')).toBe(true);
    expect(matchesSpecification(specs, 'intended_use', 'unknown')).toBe(false);
  });
});
