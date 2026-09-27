import { describe, expect, it } from "vitest";
import { reopening } from "../../src/reopen.js";

function fakeLedger(openResults) {
  const calls = [];
  return {
    calls,
    async open() {
      calls.push("open");
      const result = openResults.shift();
      if (result instanceof Error) throw result;
    },
    async close() {
      calls.push("close");
    },
    async accountBalances() {
      calls.push("accountBalances");
      return { checking: 1, cards: [] };
    },
  };
}

function fakeWait() {
  const waits = [];
  return { waits, wait: async (ms) => waits.push(ms) };
}

describe("reopening", () => {
  it("closes the half-open ledger and opens it again after a failure", async () => {
    const ledger = fakeLedger([new Error("other side closed")]);
    const { waits, wait } = fakeWait();
    const subject = reopening(ledger, { attempts: 3, delayMs: 2000, wait });

    await subject.open();

    expect(ledger.calls).toEqual(["open", "close", "open"]);
    expect(waits).toEqual([2000]);
  });

  it("rethrows the last failure without closing once attempts run out", async () => {
    const last = new Error("third");
    const ledger = fakeLedger([new Error("first"), new Error("second"), last]);
    const { waits, wait } = fakeWait();
    const subject = reopening(ledger, { attempts: 3, delayMs: 2000, wait });

    await expect(subject.open()).rejects.toBe(last);

    expect(ledger.calls).toEqual(["open", "close", "open", "close", "open"]);
    expect(waits).toEqual([2000, 2000]);
  });

  it("opens once without waiting when the first attempt succeeds", async () => {
    const ledger = fakeLedger([]);
    const { waits, wait } = fakeWait();
    const subject = reopening(ledger, { attempts: 3, delayMs: 2000, wait });

    await subject.open();

    expect(ledger.calls).toEqual(["open"]);
    expect(waits).toEqual([]);
  });

  it("passes every other ledger operation straight through", async () => {
    const ledger = fakeLedger([]);
    const subject = reopening(ledger, { attempts: 3, delayMs: 2000, wait: async () => {} });

    expect(await subject.accountBalances()).toEqual({ checking: 1, cards: [] });
    await subject.close();

    expect(ledger.calls).toEqual(["accountBalances", "close"]);
  });
});
