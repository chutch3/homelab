import { describe, expect, it, vi } from "vitest";

import { createReporter } from "../../src/reporter.js";

const config = {
  postalUrl: "http://postal.unit.test",
  postalApiKey: "unit-key",
  alertFrom: "budget@unit.test",
  alertTo: ["a@unit.test", "b@unit.test"],
};

function setup({ sendMail } = {}) {
  const metrics = { recordFailure: vi.fn() };
  const mailer = sendMail ?? vi.fn().mockResolvedValue({ message_id: "unit" });
  const log = vi.fn();
  const reportFailure = createReporter({ metrics, sendMail: mailer, config, log, now: () => 1700000000 });
  return { reportFailure, metrics, mailer, log };
}

describe("createReporter", () => {
  it("records the failure metric and emails the alert", async () => {
    const { reportFailure, metrics, mailer } = setup();

    await reportFailure(new Error("names no longer resolve"));

    expect(metrics.recordFailure).toHaveBeenCalledTimes(1);
    expect(metrics.recordFailure).toHaveBeenCalledWith({ now: 1700000000 });
    expect(mailer).toHaveBeenCalledTimes(1);
    const msg = mailer.mock.calls[0][0];
    expect(msg.to).toEqual(["a@unit.test", "b@unit.test"]);
    expect(msg.from).toBe("budget@unit.test");
    expect(msg.subject).toMatch(/beholder.*(failed|attention)/i);
    expect(msg.body).toContain("names no longer resolve");
  });

  it("logs the full stack, not just the message", async () => {
    const { reportFailure, log } = setup();
    const error = new Error("boom");

    await reportFailure(error);

    const logged = log.mock.calls.map((c) => c.join(" ")).join("\n");
    expect(logged).toContain(error.stack);
  });

  it("names every underlying cause on the run-failure line, then the stack", async () => {
    const { reportFailure, log } = setup();
    const error = new TypeError("fetch failed", {
      cause: new Error("connect ECONNREFUSED 127.0.0.1:1", { cause: "socket closed" }),
    });

    await reportFailure(error);

    const [headline, ...frames] = log.mock.calls[0][0].split("\n");
    expect(headline).toBe(
      "[beholder] run failed: TypeError: fetch failed (caused by: connect ECONNREFUSED 127.0.0.1:1) (caused by: socket closed)",
    );
    expect(frames).toEqual(error.stack.split("\n").slice(1));
  });

  it("names the cause when the failure email itself fails", async () => {
    const sendMail = vi
      .fn()
      .mockRejectedValue(
        new TypeError("fetch failed", { cause: new Error("getaddrinfo EAI_AGAIN postal.unit.test") }),
      );
    const { reportFailure, log } = setup({ sendMail });

    await reportFailure(new Error("original"));

    expect(log).toHaveBeenLastCalledWith(
      "[beholder] failure email also failed: fetch failed (caused by: getaddrinfo EAI_AGAIN postal.unit.test)",
    );
  });

  it("does not throw when the failure email itself fails", async () => {
    const sendMail = vi.fn().mockRejectedValue(new Error("postal down"));
    const { reportFailure, log } = setup({ sendMail });

    await expect(reportFailure(new Error("original"))).resolves.toBeUndefined();
    const logged = log.mock.calls.map((c) => c.join(" ")).join("\n");
    expect(logged).toContain("postal down");
  });
});
