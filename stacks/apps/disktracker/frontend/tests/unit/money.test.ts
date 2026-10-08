import { describe, expect, it } from 'vitest';
import { parseDollars } from '../../src/money';

describe('manual USD entry', () => {
  it.each([
    ['189.00', 18900], ['0.29', 29], ['0', 0], [' 10.5 ', 1050], ['', null],
  ])('converts %s to exact cents or unknown', (input, expected) => {
    expect(parseDollars(input)).toBe(expected);
  });
  it('rejects values above the API amount limit', () => {
    expect(parseDollars('10000000.00')).toBe(1_000_000_000);
    expect(() => parseDollars('10000000.01')).toThrow('Enter $10,000,000.00 or less.');
  });
  it.each(['-1', '1.005', '1e3', 'abc', 'Infinity'])('rejects %s', (input) => {
    expect(() => parseDollars(input)).toThrow('Enter a non-negative amount with up to two decimal places.');
  });
});
