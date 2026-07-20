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
  const reportFailure = createReporter({ metrics, sendMail: mailer, config, log });
  return { reportFailure, metrics, mailer, log };
}

describe("createReporter", () => {
  it("records the failure metric and emails the alert", async () => {
    const { reportFailure, metrics, mailer } = setup();

    await reportFailure(new Error("names no longer resolve"));

    expect(metrics.recordFailure).toHaveBeenCalledTimes(1);
    expect(metrics.recordFailure.mock.calls[0][0]).toHaveProperty("now", expect.any(Number));
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

  it("does not throw when the failure email itself fails", async () => {
    const sendMail = vi.fn().mockRejectedValue(new Error("postal down"));
    const { reportFailure, log } = setup({ sendMail });

    await expect(reportFailure(new Error("original"))).resolves.toBeUndefined();
    const logged = log.mock.calls.map((c) => c.join(" ")).join("\n");
    expect(logged).toContain("postal down");
  });
});
