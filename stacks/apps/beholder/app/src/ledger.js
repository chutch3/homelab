// Boundary: the only module that touches @actual-app/api.
// No household facts live here or anywhere in source — account/category
// NAMES arrive via config and are resolved against the server at open();
// watched schedules are read from the server itself.

import { mkdir } from "node:fs/promises";
import api from "@actual-app/api";

// Wide enough to survive multi-day bank-sync lag; alert dedupe in run.js
// keeps the wide window from nagging.
const RAID_LOOKBACK_DAYS = 14;
const SCHEDULE_LOOKBACK_DAYS = 35;

function isoDaysAgo(days, now = new Date()) {
  return new Date(now.getTime() - days * 86400000).toISOString().slice(0, 10);
}

function resolveByName(kind, list, name) {
  const hit = list.find((x) => x.name === name);
  if (!hit) {
    const available = list.map((x) => x.name).join(", ");
    throw new Error(`cannot resolve ${kind} '${name}' on the budget server; available: ${available}`);
  }
  return hit;
}

export function createLedger({ serverUrl, password, syncId, dataDir, names, bestEffort = (fn) => fn() }) {
  let checkingId;
  let cardIds; // [{id, name}]
  let savingsCategoryId;

  return {
    async open() {
      await mkdir(dataDir, { recursive: true }); // api.init requires it to exist
      await api.init({ dataDir, serverURL: serverUrl, password });
      await api.downloadBudget(syncId);

      const accounts = (await api.getAccounts()).filter((a) => !a.closed);
      checkingId = resolveByName("account", accounts, names.checking).id;
      cardIds = names.cards.map((n) => ({ id: resolveByName("account", accounts, n).id, name: n }));
      const categories = await api.getCategories();
      savingsCategoryId = resolveByName("category", categories, names.savingsCategory).id;

      // Pull fresh bank data before checking; stale checks beat no checks. A
      // sync failure only warns — including the out-of-band rejections the
      // Actual API throws for a bank link in trouble, which bestEffort keeps
      // from crashing the run.
      await bestEffort(async () => {
        try {
          await api.runBankSync();
        } catch (e) {
          console.warn(`[beholder] bank sync failed (continuing with last-synced data): ${e.message}`);
        }
      });
    },

    async close() {
      await api.shutdown();
    },

    async accountBalances() {
      const checking = await api.getAccountBalance(checkingId);
      const cards = [];
      for (const c of cardIds) {
        cards.push({ name: c.name, balance: await api.getAccountBalance(c.id) });
      }
      return { checking, cards };
    },

    async savingsInflows() {
      const since = isoDaysAgo(RAID_LOOKBACK_DAYS);
      const { data } = await api.runQuery(
        api
          .q("transactions")
          .filter({
            $and: [{ category: savingsCategoryId }, { date: { $gte: since } }, { amount: { $gt: 0 } }],
          })
          .select(["id", "date", "amount", "payee.name"]),
      );
      return data.map((t) => ({
        id: t.id,
        date: t.date,
        amount: t.amount,
        payee: t["payee.name"] ?? "(unknown)",
      }));
    },

    async recentTransactions() {
      const since = isoDaysAgo(SCHEDULE_LOOKBACK_DAYS);
      const { data } = await api.runQuery(
        api
          .q("transactions")
          .filter({ $and: [{ account: checkingId }, { date: { $gte: since } }] })
          .select(["date", "amount", "payee", "payee.name"]),
      );
      return data.map((t) => ({
        date: t.date,
        amount: t.amount,
        payeeId: t.payee,
        payee: t["payee.name"] ?? "(unknown)",
      }));
    },

    // Transactions on open on-budget accounts with no category; transfers
    // excluded (card payments are legitimately uncategorized).
    async uncategorizedTransactions() {
      const since = isoDaysAgo(RAID_LOOKBACK_DAYS);
      const { data } = await api.runQuery(
        api
          .q("transactions")
          .filter({
            $and: [
              { category: null },
              { "account.offbudget": false },
              { "account.closed": false },
              { date: { $gte: since } },
              { transfer_id: null },
            ],
          })
          .select(["id", "date", "amount", "payee.name", "account.name"]),
      );
      return data.map((t) => ({
        id: t.id,
        date: t.date,
        amount: t.amount,
        payee: t["payee.name"] ?? "(unknown)",
        account: t["account.name"] ?? "(unknown)",
      }));
    },

    // Every active schedule on the checking account with an exact amount is
    // a promise worth watching; approximate schedules are noise.
    async watchedSchedules() {
      const { data } = await api.runQuery(
        api
          .q("schedules")
          .filter({ completed: false, tombstone: false })
          .select(["id", "name", "_payee", "_account", "_amount", "_amountOp"]),
      );
      return data
        .filter((s) => s._account === checkingId && s._amountOp === "is" && typeof s._amount === "number")
        .map((s) => ({
          payeeId: s._payee,
          expectedAmount: s._amount,
          label: s.name || "(unnamed schedule)",
        }));
    },
  };
}
