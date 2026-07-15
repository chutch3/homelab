export function fmt(cents) {
  const abs = Math.abs(cents);
  const s = (abs / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${cents < 0 ? "-" : ""}$${s}`;
}
