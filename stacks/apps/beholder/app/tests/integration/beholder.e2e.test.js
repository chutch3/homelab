import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import net from "node:net";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import * as mockttp from "mockttp";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

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
  serverProc = spawn("node", [join(APP_DIR, "node_modules/@actual-app/sync-server/build/app.js")], {
    env: {
      ...process.env,
      ACTUAL_PORT: String(port),
      ACTUAL_DATA_DIR: dataDir,
      ACTUAL_SERVER_FILES: join(dataDir, "server-files"),
      ACTUAL_USER_FILES: join(dataDir, "user-files"),
    },
    stdio: "ignore",
  });
  await waitFor(async () => (await fetch(`${serverBase}/info`)).ok);
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
      { date: today, amount: -4599, payee_name: "Mystery Merchant" },
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
    await api.createAccount({ name: "Chase Checking", offbudget: false }, 500000);
    await api.createAccount({ name: "Discover", offbudget: false }, -100000);
    const group = await api.createCategoryGroup({ name: "Savings" });
    await api.createCategory({ name: "Wealthfront", group_id: group });
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
  serverProc?.kill("SIGTERM");
  await postal.stop();
});

function runBeholder(syncId, tmpPrefix, envOverrides = {}) {
  const stateDir = mkdtempSync(join(tmpdir(), tmpPrefix));
  const env = {
    ...process.env,
    BEHOLDER_RUN_ONCE: "1",
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
  return new Promise((res) => {
    const proc = spawn("node", ["src/index.js"], { cwd: APP_DIR, env });
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d));
    proc.stderr.on("data", (d) => (stderr += d));
    proc.on("exit", (code) => res({ code, stdout, stderr, statePath: env.BEHOLDER_STATE_PATH }));
  });
}

describe("beholder end to end", () => {
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
    expect(email.body.plain_body).toMatch(/below the card floor/);
    expect(email.body.plain_body).toMatch(/came out of savings/);
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
    expect(body).toMatch(/below the card floor/); // conditions repeat
    expect(body).not.toContain("Mystery Merchant"); // events do not
    expect(body).not.toContain("came out of savings");
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

  it("stays quiet and records a snapshot when the budget is healthy", async () => {
    const before = await sentCount();
    const run = await runBeholder(syncIds.healthy, "beholder-e2e-healthy-");
    expect(run.stderr).toBe("");
    expect(run.code).toBe(0);
    expect(await sentCount()).toBe(before);
    expect(run.stdout).toContain("(quiet)");
    const state = JSON.parse(readFileSync(run.statePath, "utf8"));
    expect(state.snapshots.length).toBe(1);
    expect(state.snapshots[0].cards).toEqual({ Discover: -100000 });
  }, 120000);
});
