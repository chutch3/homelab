import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import net from "node:net";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import * as mockttp from "mockttp";
import { chromium } from "playwright";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { startProcess } from "./fixtures/process.mjs";

// Integration per the house harness pattern: beholder runs as a REAL
// subprocess (the Dockerfile CMD) against a REAL sync-server seeded with
// fixture data; only the true external HTTP boundary (Postal) is faked —
// with mockttp (a real server on a real port, the pytest-httpserver of our
// Node tier), so unmatched requests fail loudly instead of vanishing.
// Observation is via real surfaces only: exit code, the fake's recorded
// requests, stdout, the state file. This file never imports src/.

const APP_DIR = resolve(import.meta.dirname, "../..");
const PASSWORD = "harness-pass";
const today = new Date().toISOString().slice(0, 10);
const month = today.slice(0, 7);
const previousMonth = new Date(`${month}-01T00:00:00Z`);
previousMonth.setUTCMonth(previousMonth.getUTCMonth() - 1);

async function freePort() {
  return new Promise((res) => {
    const s = net.createServer();
    s.listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => res(p));
    });
  });
}

async function waitFor(fn, timeoutMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await fn().catch(() => false)) return;
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("timeout waiting for condition");
}

let serverProc;
let serverBase;
const postal = mockttp.getLocal();
let sendEndpoint;
const syncIds = {};
const resolution = {};
const daysAgo = (days) =>
  new Date(new Date(`${today}T00:00:00Z`).getTime() - days * 86400000).toISOString().slice(0, 10);

// Recorded sends after `since`, decoded to { path, apiKey, body }.
async function sentEmails(since = 0) {
  const requests = await sendEndpoint.getSeenRequests();
  return Promise.all(
    requests.slice(since).map(async (r) => ({
      path: r.path,
      apiKey: r.headers["x-server-api-key"],
      body: await r.body.getJson(),
    })),
  );
}

async function sentCount() {
  return (await sendEndpoint.getSeenRequests()).length;
}

beforeAll(async () => {
  // 1. real sync-server on a temp dir
  const dataDir = mkdtempSync(join(tmpdir(), "beholder-e2e-server-"));
  const port = await freePort();
  serverBase = `http://127.0.0.1:${port}`;
  serverProc = startProcess("node", [join(APP_DIR, "node_modules/@actual-app/sync-server/build/app.js")], {
    env: {
      ...process.env,
      ACTUAL_PORT: String(port),
      ACTUAL_DATA_DIR: dataDir,
      ACTUAL_SERVER_FILES: join(dataDir, "server-files"),
      ACTUAL_USER_FILES: join(dataDir, "user-files"),
    },
    timeoutMs: 240000,
  });
  try {
    await waitFor(async () => (await fetch(`${serverBase}/info`)).ok);
  } catch (error) {
    throw new Error(`${error.message}
${JSON.stringify(serverProc.output())}`);
  }
  await fetch(`${serverBase}/account/bootstrap`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ password: PASSWORD }),
  });

  // 2. seed two budgets via the api (harness glue, not the code under test)
  const api = (await import("@actual-app/api")).default;
  const clientDir = mkdtempSync(join(tmpdir(), "beholder-e2e-seed-"));
  await api.init({ dataDir: clientDir, serverURL: serverBase, password: PASSWORD });

  // scenario "troubled": floor breach + savings raid + uncategorized txn
  // + a schedule whose payee posted at the wrong amount
  await api.runImport("troubled", async () => {
    const checking = await api.createAccount({ name: "Chase Checking", offbudget: false }, 5850);
    await api.createAccount({ name: "Discover", offbudget: false }, -152795);
    const group = await api.createCategoryGroup({ name: "Savings" });
    const savings = await api.createCategory({ name: "Wealthfront", group_id: group });
    const bills = await api.createCategory({ name: "Bills", group_id: group });
    await api.addTransactions(checking, [
      { date: today, amount: 75000, payee_name: "Wealthfront", category: savings },
      {
        date: today,
        amount: -4599,
        payee_name: "Mystery Merchant Beachy Bean Coffee Santa Rosa Beflapple Pay Ending in",
      },
      { date: today, amount: -11900, payee_name: "Synchrony Credit Card", category: bills },
    ]);
    const payees = await api.getPayees();
    const synchrony = payees.find((p) => p.name === "Synchrony Credit Card");
    await api.internal.send("schedule/create", {
      schedule: { name: "Furniture Bill", posts_transaction: false },
      conditions: [
        { op: "is", field: "payee", value: synchrony.id },
        { op: "is", field: "account", value: checking },
        {
          op: "isapprox",
          field: "date",
          value: {
            start: today,
            interval: 1,
            frequency: "monthly",
            patterns: [],
            skipWeekend: false,
            weekendSolveMode: "after",
            endMode: "never",
            endOccurrences: 1,
            endDate: today,
          },
        },
        { op: "is", field: "amount", value: -20000 },
      ],
    });
  });

  // scenario "healthy": comfortably above the floor, no raids
  await api.runImport("healthy", async () => {
    const checking = await api.createAccount({ name: "Chase Checking", offbudget: false }, 500000);
    await api.createAccount({ name: "Discover", offbudget: false }, -100000);
    const group = await api.createCategoryGroup({ name: "Savings" });
    await api.createCategory({ name: "Wealthfront", group_id: group });
    const carry = await api.createCategory({ name: "Carry fund", group_id: group });
    const over = await api.createCategory({ name: "Over budget", group_id: group });
    await api.createCategory({ name: "Zero fund", group_id: group });
    await api.createCategory({ name: "Hidden category", group_id: group, hidden: true });
    const hiddenGroup = await api.createCategoryGroup({ name: "Hidden group", hidden: true });
    await api.createCategory({ name: "Hidden group child", group_id: hiddenGroup });
    const income = await api.createCategoryGroup({ name: "Income group", is_income: true });
    await api.createCategory({ name: "Salary", group_id: income, is_income: true });
    await api.setBudgetAmount(previousMonth.toISOString().slice(0, 7), carry, 10000);
    await api.setBudgetAmount(month, carry, 20000);
    await api.addTransactions(checking, [
      { date: today, amount: -2500, payee_name: "Carry purchase", category: carry },
      { date: today, amount: -1234, payee_name: "Over purchase", category: over },
    ]);
  });

  await api.runImport("threshold", async () => {
    await api.createAccount({ name: "Chase Checking", offbudget: false }, 500000);
    await api.createAccount({ name: "Discover", offbudget: false }, -100000);
    await api.createAccount({ name: "Small change", offbudget: false }, -50000);
    const group = await api.createCategoryGroup({ name: "Savings" });
    await api.createCategory({ name: "Wealthfront", group_id: group });
  });

  await api.runImport("resolution", async () => {
    const checking = await api.createAccount({ name: "Chase Checking", offbudget: false }, 500000);
    await api.createAccount({ name: "Discover", offbudget: false }, -100000);
    const group = await api.createCategoryGroup({ name: "Savings" });
    await api.createCategory({ name: "Wealthfront", group_id: group });
    resolution.category = await api.createCategory({ name: "Meals", group_id: group });
    await api.setBudgetAmount(month, resolution.category, 10000);
    await api.addTransactions(checking, [{ date: today, amount: -2500, payee_name: "Needs a category" }]);
    resolution.transaction = (await api.getTransactions(checking, today, today)).find(
      (t) => t.amount === -2500,
    ).id;
  });

  await api.runImport("query-boundaries", async () => {
    const checking = await api.createAccount({ name: "Chase Checking", offbudget: false }, 500000);
    await api.createAccount({ name: "Discover", offbudget: false }, -100000);
    const offbudget = await api.createAccount({ name: "Off budget", offbudget: true }, 1000);
    const closed = await api.createAccount({ name: "Closed account", offbudget: false }, 1000);
    const target = await api.createAccount({ name: "Transfer target", offbudget: false }, 0);
    const group = await api.createCategoryGroup({ name: "Savings" });
    const savings = await api.createCategory({ name: "Wealthfront", group_id: group });
    const bills = await api.createCategory({ name: "Bills", group_id: group });
    await api.addTransactions(checking, [
      { date: daysAgo(14), amount: -100, payee_name: "Uncategorized boundary" },
      { date: daysAgo(15), amount: -200, payee_name: "Uncategorized too old" },
      { date: today, amount: -300, payee_name: "Already categorized", category: bills },
      { date: daysAgo(14), amount: 400, payee_name: "Savings boundary", category: savings },
      { date: daysAgo(15), amount: 500, payee_name: "Savings too old", category: savings },
      { date: daysAgo(35), amount: -600, payee_name: "Schedule boundary", category: bills },
      { date: daysAgo(36), amount: -700, payee_name: "Schedule too old", category: bills },
    ]);
    await api.addTransactions(offbudget, [{ date: today, amount: -1000, payee_name: "Off budget purchase" }]);
    await api.addTransactions(closed, [{ date: today, amount: -1000, payee_name: "Closed purchase" }]);
    await api.closeAccount(closed);
    const payees = await api.getPayees();
    await api.addTransactions(
      checking,
      [{ date: today, amount: -1300, payee: payees.find((p) => p.transfer_acct === target).id }],
      { runTransfers: true },
    );
    for (const name of ["Schedule boundary", "Schedule too old"]) {
      await api.internal.send("schedule/create", {
        schedule: { name, posts_transaction: false },
        conditions: [
          { op: "is", field: "payee", value: payees.find((p) => p.name === name).id },
          { op: "is", field: "account", value: checking },
          { op: "is", field: "amount", value: -20000 },
          {
            op: "isapprox",
            field: "date",
            value: {
              start: today,
              interval: 1,
              frequency: "monthly",
              patterns: [],
              skipWeekend: false,
              weekendSolveMode: "after",
              endMode: "never",
              endOccurrences: 1,
              endDate: today,
            },
          },
        ],
      });
    }
  });

  await api.runImport("duplicates", async () => {
    await api.createAccount({ name: "Chase Checking", offbudget: false }, 500000);
    const card = await api.createAccount({ name: "Discover", offbudget: false }, 0);
    const group = await api.createCategoryGroup({ name: "Spending" });
    await api.createCategory({ name: "Wealthfront", group_id: group });
    const food = await api.createCategory({ name: "Food", group_id: group });
    await api.addTransactions(card, [
      {
        date: daysAgo(7),
        amount: -100,
        payee_name: "Fuel Station",
        imported_payee: "Fuel Station",
        imported_id: "pending-fuel",
        cleared: false,
        category: food,
      },
      {
        date: daysAgo(5),
        amount: -4000,
        payee_name: "Fuel Station Downtown",
        imported_payee: "Fuel Station Downtown",
        imported_id: "posted-fuel",
        cleared: true,
        category: food,
      },
      {
        date: daysAgo(7),
        amount: -5537,
        payee_name: "Restaurant",
        imported_payee: "Restaurant",
        imported_id: "pending-meal",
        cleared: false,
        category: food,
      },
      {
        date: daysAgo(7),
        amount: -6337,
        payee_name: "Restaurant",
        imported_payee: "Restaurant",
        imported_id: "posted-meal",
        cleared: true,
        category: food,
      },
    ]);
  });

  const files = await api.internal.send("get-remote-files");
  for (const f of files) syncIds[f.name] = f.groupId ?? f.fileId;
  await api.shutdown();

  // 3. mockttp standing in for Postal: only the send endpoint is mocked, so
  // any request to a wrong path gets mockttp's loud 503 instead of silence
  await postal.start();
  sendEndpoint = await postal
    .forPost("/api/v1/send/message")
    .thenJson(200, { status: "success", data: { message_id: "e2e" } });
}, 120000);

afterAll(async () => {
  await serverProc?.stop();
  await postal.stop();
});

function startBeholder(syncId, tmpPrefix, envOverrides = {}) {
  const stateDir = mkdtempSync(join(tmpdir(), tmpPrefix));
  const env = {
    ...process.env,
    BEHOLDER_RUN_ONCE: "1",
    TZ: "UTC",
    BEHOLDER_BUDGET_URL: "https://budget.harness.test/",
    ACTUAL_SERVER_URL: serverBase,
    ACTUAL_PASSWORD: PASSWORD,
    ACTUAL_BUDGET_SYNC_ID: syncId,
    BEHOLDER_DATA_DIR: join(stateDir, "actual-data"),
    BEHOLDER_STATE_PATH: join(stateDir, "beholder.json"),
    BEHOLDER_POSTAL_URL: `http://127.0.0.1:${postal.port}`,
    BEHOLDER_POSTAL_API_KEY: "e2e-key",
    BEHOLDER_ALERT_FROM: "budget@harness.test",
    BEHOLDER_ALERT_TO: "one@harness.test,two@harness.test",
    BEHOLDER_CHECKING_ACCOUNT: "Chase Checking",
    BEHOLDER_CARD_ACCOUNTS: "Discover",
    BEHOLDER_SAVINGS_CATEGORY: "Wealthfront",
    ...envOverrides,
  };
  const child = startProcess(process.execPath, ["src/index.js"], {
    cwd: APP_DIR,
    env,
    timeoutMs: env.BEHOLDER_RUN_ONCE === "0" ? 110000 : 20000,
  });
  return {
    ...child,
    finished: child.finished.then((result) => ({ ...result, statePath: env.BEHOLDER_STATE_PATH })),
  };
}

function runBeholder(syncId, tmpPrefix, envOverrides = {}) {
  return startBeholder(syncId, tmpPrefix, envOverrides).finished;
}

describe("beholder end to end", () => {
  it("emails pending and posted duplicate candidates without changing transactions", async () => {
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-duplicates-"));
    const env = { BEHOLDER_STATE_PATH: join(dir, "state.json") };
    for (let i = 0; i < 2; i++) {
      const run = await runBeholder(syncIds.duplicates, "beholder-duplicates-client-", env);
      expect(run.code, run.stderr).toBe(0);
    }
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(2);
    for (const email of emails) {
      for (const body of [email.body.html_body, email.body.plain_body]) {
        expect(body).toContain("Possible duplicate charges");
        expect(body).toContain("Check whether the posted charge replaced the pending entry.");
        for (const value of [
          "Fuel Station",
          "Fuel Station Downtown",
          "$1.00",
          "$40.00",
          "Restaurant",
          "$55.37",
          "$63.37",
          "Pending",
          "Posted",
        ])
          expect(body).toContain(value);
      }
    }
    // A second fresh client still sees both rows; the check must never merge/delete them.
    expect(emails[1].body.plain_body).toContain("Discover: $159.74 owed");
  }, 120000);

  it.each([
    [{ BEHOLDER_DUPLICATE_LOOKBACK_DAYS: "4" }, false, false],
    [{ BEHOLDER_DUPLICATE_WINDOW_DAYS: "1" }, false, true],
    [{ BEHOLDER_DUPLICATE_MAX_INCREASE_PERCENT: "10" }, true, false],
    [{ BEHOLDER_DUPLICATE_HOLD_MAX_CENTS: "0" }, false, true],
    [{ BEHOLDER_DUPLICATE_MAX_INCREASE_PERCENT: "0", BEHOLDER_DUPLICATE_HOLD_MAX_CENTS: "0" }, false, false],
  ])(
    "applies duplicate review environment overrides %#",
    async (env, fuel, meal) => {
      const before = await sentCount();
      const run = await runBeholder(syncIds.duplicates, "beholder-duplicate-overrides-", env);
      expect(run.code, run.stderr).toBe(0);
      const emails = await sentEmails(before);
      expect(emails).toHaveLength(1);
      for (const body of [emails[0].body.html_body, emails[0].body.plain_body]) {
        expect(body.includes("Fuel Station")).toBe(fuel);
        expect(body.includes("Restaurant")).toBe(meal);
        expect(body.includes("Possible duplicate charges")).toBe(fuel || meal);
      }
    },
    120000,
  );

  it("keeps duplicate pairs together and readable at phone width", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.duplicates, "beholder-duplicate-layout-");
    expect(run.code, run.stderr).toBe(0);
    const [email] = await sentEmails(before);
    const browser = await chromium.launch({ headless: true });
    try {
      const page = await browser.newPage({ viewport: { width: 320, height: 900 } });
      await page.setContent(email.body.html_body);
      const tables = page.getByRole("table", { name: "Possible duplicate charges", exact: true });
      expect(await tables.count()).toBe(2);
      const date = (value) =>
        new Date(`${value}T00:00:00Z`).toLocaleDateString("en-US", {
          timeZone: "UTC",
          month: "long",
          day: "numeric",
          year: "numeric",
        });
      expect(
        await tables
          .first()
          .locator("tbody tr")
          .evaluateAll((rows) => rows.map((row) => Array.from(row.cells, (cell) => cell.textContent))),
      ).toEqual([
        ["Pending", date(daysAgo(7)), "Fuel Station", "$1.00"],
        ["Posted", date(daysAgo(5)), "Fuel Station Downtown", "$40.00"],
      ]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
      const sizes = await tables
        .locator("td")
        .evaluateAll((cells) => cells.map((cell) => cell.getBoundingClientRect().right));
      for (const right of sizes) expect(right).toBeLessThanOrEqual(320);
    } finally {
      await browser.close();
    }
  }, 120000);

  it("delivers monthly spending totals and tables explaining savings and payment differences", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.troubled, "beholder-tables-");
    expect(run.code, run.stderr).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(1);
    const { html_body: html, plain_body: text } = emails[0].body;
    for (const body of [html, text]) {
      for (const label of [
        "Account balances",
        "Current checking and credit-card balances.",
        "Monthly spending",
        "$119.00 spent of $0.00 budgeted · No monthly budget",
        "Savings transactions to review",
        "Confirm these transactions belong in the savings category.",
        "Payment differs from schedule",
        "Scheduled",
        "Recorded",
        "Difference",
        "$81.00 less",
      ])
        expect(body).toContain(label);
      expect(body).not.toContain("Can checking cover the cards?");
      expect(body).not.toContain("Total card debt");
      expect(body).not.toContain("Items to review");
      expect(body).not.toContain("Categorize these transactions in Actual.");
    }
    expect(html).toContain('aria-label="Savings transactions to review"');
    expect(html).toContain('aria-label="Payment differs from schedule"');
    expect(html).toContain(
      'aria-label="Monthly spending: $119.00 spent of $0.00 budgeted · No monthly budget"',
    );
  }, 120000);

  it("delivers alphabetical category lookup with carryover-aware spending bars before accounts", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.healthy, "beholder-category-lookup-");
    expect(run.code, run.stderr).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(1);
    for (const body of [emails[0].body.html_body, emails[0].body.plain_body]) {
      for (const label of [
        "Open budget",
        "Left to spend",
        "Monthly spending",
        "$37.34 spent of $200.00 budgeted · 19% spent",
        "Carry fund",
        "$275.00 left",
        "$25.00 spent of $300.00 available",
        "Account balances",
      ])
        expect(body).toContain(label);
      expect(body.indexOf("Monthly spending")).toBeLessThan(body.indexOf("Open budget"));
      expect(body.indexOf("Open budget")).toBeLessThan(body.indexOf("Left to spend"));
      expect(body.indexOf("Carry fund")).toBeLessThan(body.indexOf("Over budget"));
      expect(body.indexOf("Zero fund")).toBeLessThan(body.indexOf("Account balances"));
    }
    expect(emails[0].body.html_body).toContain('aria-label="Carry fund: 8% spent"');
    expect(emails[0].body.html_body).toContain(
      'aria-label="Monthly spending: $37.34 spent of $200.00 budgeted · 19% spent"',
    );
  }, 120000);

  it("preview download failure exits without sending a report or a failure email", async () => {
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-preview-download-failure-"));
    const output = join(dir, "preview.html");
    const run = await runBeholder("missing-budget", "beholder-preview-missing-", {
      BEHOLDER_PREVIEW_OUTPUT: output,
      BEHOLDER_PREVIEW_TO: "preview@harness.test",
    });
    expect(run.code).toBe(1);
    expect(run.stderr).toContain("preview failed:");
    expect(run.stderr).not.toContain("[beholder] run failed:");
    expect(await sentCount()).toBe(before);
    expect(() => readFileSync(output)).toThrow(/ENOENT/);
    expect(() => readFileSync(run.statePath)).toThrow(/ENOENT/);
  }, 120000);

  it("previews a budget migrated by Actual 26.7.0 through the 26.5.2 server", async () => {
    const login = await fetch(`${serverBase}/account/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password: PASSWORD }),
    });
    const {
      data: { token },
    } = await login.json();
    const upload = await fetch(`${serverBase}/sync/upload-user-file`, {
      method: "POST",
      headers: {
        "content-type": "application/encrypted-file",
        "x-actual-token": token,
        "x-actual-file-id": "769a56b4-3e5d-40fa-b94e-341ccca11096",
        "x-actual-name": "Migration compatibility fixture",
        "x-actual-format": "2",
      },
      body: readFileSync(join(APP_DIR, "tests/integration/fixtures/actual-26.7.0.zip")),
    });
    expect(upload.status).toBe(200);
    const { groupId } = await upload.json();
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-migrated-preview-"));
    const output = join(dir, "preview.html");
    const run = await runBeholder(groupId, "beholder-migrated-client-", {
      BEHOLDER_PREVIEW_OUTPUT: output,
    });
    expect(run.code, run.stderr).toBe(0);
    expect(readFileSync(output, "utf8")).toContain("Groceries");
    expect(readFileSync(output, "utf8")).toContain("$1,000.00");
    expect(run.stderr).not.toContain("out-of-sync-migrations");
    expect(await sentCount()).toBe(before);
    expect(() => readFileSync(run.statePath)).toThrow(/ENOENT/);
  }, 120000);

  it("previews an older snapshot with account-group updates in the sync stream", async () => {
    // The fixture server already uses these protocol types. Only seed its external API;
    // Beholder itself is invoked through src/index.js below.
    const { SyncProtoBuf } = await import("@actual-app/crdt");
    const login = await fetch(`${serverBase}/account/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password: PASSWORD }),
    });
    const {
      data: { token },
    } = await login.json();
    const fileId = "3e53ed0a-d560-4e76-8e83-03f86060f127";
    const upload = await fetch(`${serverBase}/sync/upload-user-file`, {
      method: "POST",
      headers: {
        "content-type": "application/encrypted-file",
        "x-actual-token": token,
        "x-actual-file-id": fileId,
        "x-actual-name": "Account group sync fixture",
        "x-actual-format": "2",
      },
      body: readFileSync(join(APP_DIR, "tests/integration/fixtures/actual-26.7.0.zip")),
    });
    expect(upload.status).toBe(200);
    const { groupId } = await upload.json();
    const message = new SyncProtoBuf.Message();
    message.setDataset("accounts");
    message.setRow("bedd2503-34a8-4317-8d20-9c110b3f3242");
    message.setColumn("account_group_id");
    message.setValue("0:"); // A newer client clearing the account's group.
    const envelope = new SyncProtoBuf.MessageEnvelope();
    envelope.setTimestamp(`${new Date().toISOString()}-0000-0123456789abcdef`);
    envelope.setIsencrypted(false);
    envelope.setContent(message.serializeBinary());
    const sync = new SyncProtoBuf.SyncRequest();
    sync.setFileid(fileId);
    sync.setGroupid(groupId);
    sync.setSince("1970-01-01T00:00:00.000Z-0000-0000000000000000");
    sync.addMessages(envelope);
    const response = await fetch(`${serverBase}/sync/sync`, {
      method: "POST",
      headers: { "content-type": "application/actual-sync", "x-actual-token": token },
      body: Buffer.from(sync.serializeBinary()),
    });
    expect(response.status).toBe(200);
    const output = join(mkdtempSync(join(tmpdir(), "beholder-account-group-")), "preview.html");
    const before = await sentCount();
    const run = await runBeholder(groupId, "beholder-account-group-client-", {
      BEHOLDER_PREVIEW_OUTPUT: output,
    });
    expect(run.code, run.stderr).toBe(0);
    expect(run.stderr).not.toMatch(/invalid-schema|no such column/);
    expect(readFileSync(output, "utf8")).toContain("Groceries");
    expect(readFileSync(output, "utf8")).toContain("$5,000.00");
    expect(await sentCount()).toBe(before);
    expect(() => readFileSync(run.statePath)).toThrow(/ENOENT/);
  }, 120000);

  it("preview writes current HTML without Postal credentials or changing history", async () => {
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-preview-"));
    const output = join(dir, "preview with spaces.html");
    const statePath = join(dir, "history.json");
    const original = JSON.stringify({ snapshots: [{ date: daysAgo(30), cards: { Discover: -50000 } }] });
    writeFileSync(statePath, original);
    const run = await runBeholder(syncIds.healthy, "beholder-preview-client-", {
      BEHOLDER_PREVIEW_OUTPUT: output,
      BEHOLDER_STATE_PATH: statePath,
      BEHOLDER_POSTAL_API_KEY: "",
      BEHOLDER_POSTAL_URL: "",
      BEHOLDER_ALERT_TO: "",
    });
    expect(run.code, run.stderr).toBe(0);
    const html = readFileSync(output, "utf8");
    expect(html).toContain("Carry fund");
    expect(html).toContain("$275.00 left");
    expect(html).toContain("$500.00");
    expect(html).not.toContain("Hidden category");
    expect(readFileSync(statePath, "utf8")).toBe(original);
    expect(await sentCount()).toBe(before);
    expect(run.stdout).toContain(output);
  }, 120000);

  it("preview sends the generated HTML only to the explicitly selected recipient", async () => {
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-preview-send-"));
    const output = join(dir, "preview.html");
    const run = await runBeholder(syncIds.troubled, "beholder-preview-send-client-", {
      BEHOLDER_PREVIEW_OUTPUT: output,
      BEHOLDER_PREVIEW_TO: "preview@harness.test",
    });
    expect(run.code, run.stderr).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(1);
    expect(emails[0].body.to).toEqual(["preview@harness.test"]);
    expect(emails[0].body.html_body).toBe(readFileSync(output, "utf8"));
    expect(emails[0].body.plain_body).toContain("Mystery Merchant");
    expect(() => readFileSync(run.statePath)).toThrow(/ENOENT/);
  }, 120000);

  it("preview output failure exits nonzero without sending mail or saving state", async () => {
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-preview-error-"));
    const run = await runBeholder(syncIds.healthy, "beholder-preview-error-client-", {
      BEHOLDER_PREVIEW_OUTPUT: dir,
      BEHOLDER_PREVIEW_TO: "preview@harness.test",
    });
    expect(run.code).toBe(1);
    expect(run.stderr).toContain("EISDIR");
    expect(await sentCount()).toBe(before);
    expect(() => readFileSync(run.statePath)).toThrow(/ENOENT/);
  }, 120000);

  it("daemon serves metrics, sends on schedule and shuts down cleanly", async () => {
    const before = await sentCount();
    const next = new Date(Date.now() + 65000);
    const runAt = `${String(next.getUTCHours()).padStart(2, "0")}:${String(next.getUTCMinutes()).padStart(2, "0")}`;
    const child = startBeholder(syncIds.healthy, "beholder-daemon-", {
      BEHOLDER_RUN_ONCE: "0",
      BEHOLDER_RUN_AT: runAt,
    });
    try {
      await waitFor(async () => (await fetch("http://127.0.0.1:9090/metrics")).ok);
      const initial = await (await fetch("http://127.0.0.1:9090/metrics")).text();
      expect(initial).toContain("beholder_last_run_success 0");
      for (const check of ["floor", "raid", "drift", "schedule", "uncategorized", "duplicates"])
        expect(initial).toContain(`beholder_findings{check="${check}"} 0`);
      const missing = await fetch("http://127.0.0.1:9090/nope");
      expect(missing.status).toBe(404);
      expect(await missing.text()).toBe("not found");
      expect(await sentCount()).toBe(before);
      await waitFor(async () => (await sentCount()) === before + 1, 80000);
      await waitFor(async () =>
        /^beholder_last_run_success 1$/m.test(await (await fetch("http://127.0.0.1:9090/metrics")).text()),
      );
      const metrics = await (await fetch("http://127.0.0.1:9090/metrics")).text();
      expect(metrics).toContain('beholder_runs_total{outcome="success"} 1');
      expect(metrics).toMatch(/beholder_last_run_timestamp_seconds [1-9][0-9]+/);
      expect(metrics).toMatch(/beholder_run_duration_seconds [0-9.]+/);
      expect((await fetch("http://127.0.0.1:9090/metrics")).headers.get("content-type")).toContain(
        "text/plain",
      );
      const emails = await sentEmails(before);
      expect(emails).toHaveLength(1);
      expect(emails[0].body.plain_body).toContain("Carry fund: $275.00 left");
    } finally {
      await child.stop();
    }
    const result = await child.finished;
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("SIGTERM received, exiting");
  }, 110000);

  it("updates category balances and removes resolved transactions on the next real run", async () => {
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-resolution-state-"));
    const shared = {
      BEHOLDER_STATE_PATH: join(dir, "beholder.json"),
      BEHOLDER_DATA_DIR: join(dir, "actual"),
    };
    const first = await runBeholder(syncIds.resolution, "beholder-resolution-first-", shared);
    expect(first.code).toBe(0);
    const api = (await import("@actual-app/api")).default;
    await api.init({
      dataDir: mkdtempSync(join(tmpdir(), "beholder-resolution-edit-")),
      serverURL: serverBase,
      password: PASSWORD,
    });
    try {
      await api.downloadBudget(syncIds.resolution);
      await api.updateTransaction(resolution.transaction, { category: resolution.category });
      await api.sync();
    } finally {
      await api.shutdown();
    }
    const second = await runBeholder(syncIds.resolution, "beholder-resolution-second-", shared);
    expect(second.code).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(2);
    expect(emails[0].body.plain_body).toContain("Meals: $100.00 left");
    expect(emails[0].body.plain_body).toContain("Needs a category");
    expect(emails[1].body.plain_body).toContain("Meals: $75.00 left");
    for (const body of [emails[1].body.plain_body, emails[1].body.html_body]) {
      expect(body).not.toContain("Needs a category");
      expect(body).not.toContain("Transactions to categorize");
    }
  }, 120000);

  it("applies transaction lookback boundaries and account/transfer exclusions in Actual", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds["query-boundaries"], "beholder-query-boundaries-");
    expect(run.code).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(1);
    for (const body of [emails[0].body.plain_body, emails[0].body.html_body]) {
      for (const included of ["Uncategorized boundary", "Savings boundary", "Schedule boundary"])
        expect(body).toContain(included);
      for (const excluded of [
        "Uncategorized too old",
        "Savings too old",
        "Schedule too old",
        "Off budget purchase",
        "Closed purchase",
        "Transfer target",
        "Already categorized",
      ])
        expect(body).not.toContain(excluded);
    }
    expect(run.stdout).toContain("3 finding(s)");
  }, 120000);

  it("reports a failed state write and exits nonzero", async () => {
    const before = await sentCount();
    const directory = mkdtempSync(join(tmpdir(), "beholder-unwritable-state-"));
    const run = await runBeholder(syncIds.healthy, "beholder-write-failure-", {
      BEHOLDER_STATE_PATH: directory,
    });
    expect(run.code).toBe(1);
    expect(run.stderr).toMatch(/EISDIR/);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(2);
    expect(emails[0].body.subject).toContain("budget");
    expect(emails[1].body.subject).toContain("run failed");
  }, 120000);

  it("preserves existing history on rejection and retries events successfully", async () => {
    const before = await sentCount();
    const dir = mkdtempSync(join(tmpdir(), "beholder-e2e-retry-"));
    const path = join(dir, "beholder.json");
    const original = JSON.stringify({ snapshots: [], alerted: { "raid:older-event": today } });
    writeFileSync(path, original);
    const failingPostal = mockttp.getLocal();
    await failingPostal.start();
    await failingPostal.forPost("/api/v1/send/message").thenJson(503, { status: "error" });
    try {
      const failed = await runBeholder(syncIds.troubled, "beholder-e2e-retry-failed-", {
        BEHOLDER_STATE_PATH: path,
        BEHOLDER_POSTAL_URL: failingPostal.url,
      });
      expect(failed.code).toBe(1);
      expect(readFileSync(path, "utf8")).toBe(original);
    } finally {
      await failingPostal.stop();
    }
    const retry = await runBeholder(syncIds.troubled, "beholder-e2e-retry-ok-", {
      BEHOLDER_STATE_PATH: path,
    });
    expect(retry.code).toBe(0);
    expect(retry.stdout).toContain("4 finding(s)");
    const next = await runBeholder(syncIds.troubled, "beholder-e2e-retry-next-", {
      BEHOLDER_STATE_PATH: path,
    });
    expect(next.code).toBe(0);
    expect(next.stdout).toContain("1 finding(s)");
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(2);
    expect(emails[0].body.plain_body).toContain("Savings transactions to review");
    expect(emails[1].body.plain_body).not.toContain("Savings transactions to review");
    expect(JSON.parse(readFileSync(path, "utf8")).alerted["raid:older-event"]).toBe(today);
  }, 120000);

  it.each([
    { threshold: "30000", visible: false },
    { threshold: "20000", visible: true },
  ])("uses drift threshold $threshold for each card shown in the email", async ({ threshold, visible }) => {
    const before = await sentCount();
    const stateDir = mkdtempSync(join(tmpdir(), "beholder-e2e-threshold-"));
    const statePath = join(stateDir, "beholder.json");
    const baselineDate = new Date(`${today}T00:00:00Z`);
    baselineDate.setUTCDate(baselineDate.getUTCDate() - 1);
    writeFileSync(
      statePath,
      JSON.stringify({
        snapshots: [
          {
            date: baselineDate.toISOString().slice(0, 10),
            checking: 500000,
            cards: { Discover: -50000, "Small change": -25000 },
          },
        ],
      }),
    );
    const run = await runBeholder(syncIds.threshold, "beholder-e2e-threshold-client-", {
      BEHOLDER_STATE_PATH: statePath,
      BEHOLDER_CARD_ACCOUNTS: "Discover, Small change",
      BEHOLDER_DRIFT_THRESHOLD_CENTS: threshold,
    });
    expect(run.code).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(1);
    expect(emails[0].body.plain_body).toContain("Discover's balance increased by $500.00");
    expect(emails[0].body.plain_body.includes("Small change's balance increased by $250.00")).toBe(visible);
    expect(emails[0].body.html_body.includes("Small change&#39;s balance increased by $250.00")).toBe(
      visible,
    );
  }, 120000);

  it("sends visible spending balances with carryover in HTML and plain text", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.healthy, "beholder-e2e-categories-");
    expect(run.code).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(1);
    const { html_body: html, plain_body: text, subject } = emails[0].body;
    expect(typeof html).toBe("string");
    expect(typeof text).toBe("string");
    expect(subject).toContain("budget");
    expect(text).toContain("Carry fund: $275.00 left");
    expect(text).toContain("Over budget: $12.34 over");
    expect(text).toContain("Zero fund: $0.00 left");
    for (const name of ["Hidden category", "Hidden group child", "Salary"]) {
      expect(text).not.toContain(name);
      expect(html).not.toContain(name);
    }
    expect(html).toContain("Carry fund");
    expect(html).toContain("$275.00 left");
    expect(html).toContain('href="https://budget.harness.test/"');
    expect(html).toContain("Over budget");
    expect(html.indexOf("Carry fund")).toBeLessThan(html.indexOf("Over budget"));
    expect(text).not.toContain("no email means");
  }, 120000);

  it("leaves notification state unchanged after Postal rejects the daily email", async () => {
    const failingPostal = mockttp.getLocal();
    await failingPostal.start();
    await failingPostal.forPost("/api/v1/send/message").thenJson(503, { status: "error" });
    try {
      const run = await runBeholder(syncIds.troubled, "beholder-e2e-rejected-", {
        BEHOLDER_POSTAL_URL: `http://127.0.0.1:${failingPostal.port}`,
      });
      expect(run.code).toBe(1);
      expect(run.stderr).toContain("postal send failed: HTTP 503");
      expect(() => readFileSync(run.statePath)).toThrow(/ENOENT/);
    } finally {
      await failingPostal.stop();
    }
  }, 120000);

  it("alerts by email when the budget is in trouble", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.troubled, "beholder-e2e-troubled-");
    expect(run.stderr).toBe("");
    expect(run.code).toBe(0);
    const emails = await sentEmails(before);
    expect(emails.length).toBe(1);
    const [email] = emails;
    expect(email.path).toBe("/api/v1/send/message");
    expect(email.apiKey).toBe("e2e-key");
    expect(email.body.to).toEqual(["one@harness.test", "two@harness.test"]);
    expect(email.body.from).toBe("budget@harness.test");
    expect(email.body.plain_body).toContain("Monthly spending");
    expect(email.body.plain_body).toContain("Savings transactions to review");
    expect(email.body.plain_body).toContain("Total: $750.00");
    expect(email.body.plain_body).toContain("Mystery Merchant");
    expect(email.body.plain_body).toContain("Furniture Bill");
    expect(email.body.plain_body).toContain("$119.00");
    expect(email.body.plain_body).toContain("$200.00");
    expect(run.stdout).toContain("4 finding(s)");
  }, 120000);

  it("repeats condition findings but not event findings across real runs sharing state", async () => {
    const before = await sentCount();
    const stateDir = mkdtempSync(join(tmpdir(), "beholder-e2e-dedupe-"));
    const shared = {
      BEHOLDER_DATA_DIR: join(stateDir, "actual-data"),
      BEHOLDER_STATE_PATH: join(stateDir, "beholder.json"),
    };

    const first = await runBeholder(syncIds.troubled, "beholder-e2e-dedupe-ignored-", shared);
    expect(first.code).toBe(0);
    let emails = await sentEmails(before);
    expect(emails.length).toBe(1);
    expect(emails[0].body.plain_body).toContain("Mystery Merchant");

    const second = await runBeholder(syncIds.troubled, "beholder-e2e-dedupe-ignored-", shared);
    expect(second.code).toBe(0);
    expect(second.stdout).toContain("1 finding(s)");
    emails = await sentEmails(before);
    expect(emails.length).toBe(2);
    const body = emails[1].body.plain_body;
    expect(body).toContain("Monthly spending");
    expect(body).toContain("Mystery Merchant"); // unresolved context remains
    expect(body).toContain("Transactions to categorize");
    expect(body).not.toContain("Savings transactions to review");
    expect(body).not.toContain("Furniture Bill");
  }, 120000);

  it("emails the failure and exits nonzero when a run cannot complete", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.healthy, "beholder-e2e-broken-", {
      BEHOLDER_SAVINGS_CATEGORY: "Renamed Category That Does Not Exist",
    });
    expect(run.code).toBe(1);
    // a watchdog must not fail silently: the failure itself gets emailed
    const emails = await sentEmails(before);
    expect(emails.length).toBe(1);
    expect(emails[0].body.subject).toMatch(/beholder.*(failed|broken)/i);
    expect(emails[0].body.plain_body).toContain("Renamed Category That Does Not Exist");
    expect(emails[0].body.to).toEqual(["one@harness.test", "two@harness.test"]);
  }, 120000);

  it("sends a daily update and records a snapshot when the budget is healthy", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.healthy, "beholder-e2e-healthy-");
    expect(run.stderr).toBe("");
    expect(run.code).toBe(0);
    expect(await sentCount()).toBe(before + 1);
    expect(run.stdout).toContain("daily update sent");
    const state = JSON.parse(readFileSync(run.statePath, "utf8"));
    expect(state.snapshots.length).toBe(1);
    expect(state.snapshots[0].cards).toEqual({ Discover: -100000 });
  }, 120000);
});

describe("delivered email rendering", () => {
  it("renders the delivered report at phone and desktop widths", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.troubled, "beholder-browser-");
    expect(run.code, run.stderr).toBe(0);
    const emails = await sentEmails(before);
    expect(emails).toHaveLength(1);
    const report = { html: emails[0].body.html_body, subject: emails[0].body.subject };
    const artifacts = mkdtempSync(join(tmpdir(), "beholder-email-browser-"));
    const browser = await chromium.launch({ headless: true });
    try {
      for (const width of [320, 375, 1440]) {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        try {
          await page.setContent(report.html);
          const theme = await page.evaluate(() => {
            const body = getComputedStyle(document.body);
            const link = getComputedStyle(document.querySelector("a"));
            const accounts = getComputedStyle(document.querySelector('table[aria-label="Account balances"]'));
            return {
              background: body.backgroundColor,
              text: body.color,
              button: link.backgroundColor,
              table: accounts.backgroundColor,
            };
          });
          expect(theme).toEqual({
            background: "rgb(8, 8, 17)",
            text: "rgb(217, 226, 236)",
            button: "rgb(148, 70, 237)",
            table: "rgb(36, 59, 83)",
          });
          expect(await page.locator('meta[name="color-scheme"]').getAttribute("content")).toBe("dark");

          expect(await page.getByRole("heading", { level: 1 }).innerText()).toBe(report.subject);
          expect(await page.getByRole("link", { name: "Open budget" }).getAttribute("href")).toBe(
            "https://budget.harness.test/",
          );
          expect(await page.getByRole("row").filter({ hasText: "Bills" }).innerText()).toContain(
            "$119.00 over",
          );
          const positions = await page
            .locator("h2")
            .evaluateAll((headings) =>
              headings.map((h) => ({ text: h.textContent, y: h.getBoundingClientRect().top })),
            );
          expect(positions.map((h) => h.text)).toEqual([
            "Monthly spending",
            "Left to spend",
            "Account balances",
            "Savings transactions to review",
            "Payment differs from schedule",
            "Transactions needing categories · 1",
          ]);
          expect(
            await page
              .getByRole("table", { name: "Savings transactions to review", exact: true })
              .innerText(),
          ).toContain("$750.00");
          expect(
            await page.getByRole("table", { name: "Payment differs from schedule", exact: true }).innerText(),
          ).toContain("$81.00 less");
          for (const [name, rows] of [
            [
              "Account balances",
              [
                ["Checking", "$643.51"],
                ["Discover", "$1,527.95 owed"],
              ],
            ],
            [
              "Savings transactions to review",
              [
                [
                  new Date(`${today}T00:00:00Z`).toLocaleDateString("en-US", {
                    timeZone: "UTC",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  }),
                  "Wealthfront",
                  "$750.00",
                ],
                ["", "Total", "$750.00"],
              ],
            ],
            [
              "Payment differs from schedule",
              [
                ["Scheduled", "$200.00"],
                ["Recorded", "$119.00"],
                ["Difference", "$81.00 less"],
              ],
            ],
          ]) {
            expect(
              await page
                .getByRole("table", { name, exact: true })
                .locator("tbody tr")
                .evaluateAll((rows) => rows.map((row) => Array.from(row.cells, (cell) => cell.textContent))),
            ).toEqual(rows);
          }
          const colors = await page.evaluate(() => ({
            total: getComputedStyle(
              document.querySelector(
                'table[aria-label="Savings transactions to review"] tbody tr:last-child',
              ),
            ).backgroundColor,
            overspent: getComputedStyle(
              document.querySelector('table[aria-label="Bills: No funds available"] td'),
            ).backgroundColor,
            summary: getComputedStyle(document.querySelector('table[aria-label^="Monthly spending:"] td'))
              .backgroundColor,
            warning: getComputedStyle(document.querySelector("strong").parentElement).color,
          }));
          expect(colors).toEqual({
            total: "rgb(51, 78, 104)",
            overspent: "rgb(255, 155, 155)",
            summary: "rgb(255, 155, 155)",
            warning: "rgb(245, 227, 93)",
          });
          const amountLines = await page
            .getByRole("table", { name: "Savings transactions to review", exact: true })
            .locator("td:last-child")
            .evaluateAll((cells) =>
              cells.map((cell) => {
                const range = document.createRange();
                range.selectNodeContents(cell);
                return range.getClientRects().length;
              }),
            );
          expect(amountLines).toEqual([1, 1]);
          const dimensions = await page.evaluate(() => ({
            content: document.documentElement.scrollWidth,
            viewport: innerWidth,
          }));
          expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
          const cells = await page.locator("td").evaluateAll((nodes) =>
            nodes.map((node) => ({
              left: node.getBoundingClientRect().left,
              right: node.getBoundingClientRect().right,
            })),
          );
          for (const cell of cells) {
            expect(cell.left).toBeGreaterThanOrEqual(0);
            expect(cell.right).toBeLessThanOrEqual(width);
          }
          expect(await page.locator("img,script").count()).toBe(0);
          await page.screenshot({ path: join(artifacts, `email-${width}.png`), fullPage: true });
        } finally {
          await page.close();
        }
      }
    } finally {
      await browser.close();
    }
  }, 30000);
});
