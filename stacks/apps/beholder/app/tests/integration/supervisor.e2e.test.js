import { spawn } from "node:child_process";
import { resolve } from "node:path";

import * as mockttp from "mockttp";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

// The supervisor runs in a REAL child process against mockttp standing in for
// Postal. Observed only through real surfaces: child exit code and captured
// failure emails. No src/ import here — the child does that.

const HARNESS = resolve(import.meta.dirname, "fixtures/supervisor-harness.mjs");
const postal = mockttp.getLocal();
let sendEndpoint;

beforeAll(async () => {
  await postal.start();
  sendEndpoint = await postal
    .forPost("/api/v1/send/message")
    .thenJson(200, { status: "success", data: { message_id: "e2e" } });
});

afterAll(async () => {
  await postal.stop();
});

function runHarness(mode) {
  return new Promise((res) => {
    const proc = spawn("node", [HARNESS], {
      env: { ...process.env, MODE: mode, POSTAL_URL: `http://127.0.0.1:${postal.port}` },
    });
    let stdout = "";
    proc.stdout.on("data", (d) => (stdout += d));
    proc.on("exit", (code) => res({ code, stdout }));
  });
}

describe("supervisor in a real process", () => {
  it("emails the failure and exits nonzero when a rejection escapes the run", async () => {
    const before = (await sendEndpoint.getSeenRequests()).length;

    const run = await runHarness("fatal");

    expect(run.code).toBe(1);
    const requests = (await sendEndpoint.getSeenRequests()).slice(before);
    expect(requests.length).toBe(1);
    const msg = await requests[0].body.getJson();
    expect(msg.subject).toMatch(/beholder.*(failed|attention)/i);
    expect(msg.body).toContain("out-of-band fatal");
  }, 20000);

  it("tolerates a rejection raised during best-effort work and completes", async () => {
    const before = (await sendEndpoint.getSeenRequests()).length;

    const run = await runHarness("suppressed");

    expect(run.code).toBe(0);
    expect(run.stdout).toContain("run continued");
    expect((await sendEndpoint.getSeenRequests()).slice(before).length).toBe(0);
  }, 20000);
});
