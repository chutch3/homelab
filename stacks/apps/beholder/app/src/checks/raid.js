// Report positive activity in the configured savings category without inferring its source.
export function raidCheck({ savingsInflows }) {
  if (!savingsInflows || savingsInflows.length === 0) return null;
  const total = savingsInflows.reduce((s, t) => s + t.amount, 0);
  return {
    check: "raid",
    total,
    transactions: savingsInflows.map((transaction) => ({ ...transaction })),
  };
}
