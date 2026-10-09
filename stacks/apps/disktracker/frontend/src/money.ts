export function parseDollars(input: string): number | null {
  const text = input.trim();
  if (!text) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(text)) {
    throw new Error('Enter a non-negative amount with up to two decimal places.');
  }
  const [whole, fraction = ''] = text.split('.');
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(cents) || cents > 1_000_000_000) {
    throw new Error('Enter $10,000,000.00 or less.');
  }
  return cents;
}
