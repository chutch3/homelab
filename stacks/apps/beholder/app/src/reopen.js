// The Actual API can't be initialized twice, so close before reopening.
export function reopening(ledger, { attempts, delayMs, wait }) {
  return {
    ...ledger,
    async open() {
      for (let attempt = 1; ; attempt++) {
        try {
          return await ledger.open();
        } catch (error) {
          if (attempt >= attempts) throw error;
          await ledger.close();
          await wait(delayMs);
        }
      }
    },
  };
}
