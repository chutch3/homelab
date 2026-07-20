import { EventEmitter } from "node:events";

import { describe, expect, it, vi } from "vitest";

import { createSupervisor } from "../../src/supervisor.js";

// `proc` and `exit` are injected seams so tests drive a real emitter and a spied
// exit instead of mutating the global process.
function setup({ onFatal } = {}) {
  const proc = new EventEmitter();
  const exit = vi.fn();
  const log = vi.fn();
  const reporter = onFatal ?? vi.fn().mockResolvedValue(undefined);
  const supervisor = createSupervisor({ proc, onFatal: reporter, exit, log });
  return { proc, exit, log, onFatal: reporter, supervisor };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

describe("createSupervisor — fatal handling", () => {
  it("reports and exits nonzero on an unhandled rejection outside best-effort work", async () => {
    const { proc, exit, onFatal } = setup();
    const error = new Error("real fatal");

    proc.emit("unhandledRejection", error);
    await flush();

    expect(onFatal).toHaveBeenCalledWith(error);
    expect(exit).toHaveBeenCalledWith(1);
  });

  it("reports and exits nonzero on an uncaught exception", async () => {
    const { proc, exit, onFatal } = setup();
    const error = new Error("splat");

    proc.emit("uncaughtException", error);
    await flush();

    expect(onFatal).toHaveBeenCalledWith(error);
    expect(exit).toHaveBeenCalledWith(1);
  });

  it("does not exit until the reporter has finished (email before exit)", async () => {
    let release;
    const onFatal = vi.fn(() => new Promise((r) => (release = r)));
    const { proc, exit } = setup({ onFatal });

    proc.emit("unhandledRejection", new Error("boom"));
    await flush();
    expect(onFatal).toHaveBeenCalled();
    expect(exit).not.toHaveBeenCalled();

    release();
    await flush();
    expect(exit).toHaveBeenCalledWith(1);
  });

  it("still exits nonzero when the reporter itself fails", async () => {
    const onFatal = vi.fn().mockRejectedValue(new Error("postal down too"));
    const { proc, exit } = setup({ onFatal });

    proc.emit("unhandledRejection", new Error("boom"));
    await flush();

    expect(exit).toHaveBeenCalledWith(1);
  });

  it("reports and exits only once when several fatal events fire", async () => {
    const { proc, exit, onFatal } = setup();

    proc.emit("unhandledRejection", new Error("first"));
    proc.emit("uncaughtException", new Error("second"));
    await flush();

    expect(onFatal).toHaveBeenCalledTimes(1);
    expect(exit).toHaveBeenCalledTimes(1);
  });
});

describe("createSupervisor — best-effort suppression", () => {
  it("suppresses (does not treat as fatal) a rejection raised during best-effort work", async () => {
    const { proc, exit, onFatal, log, supervisor } = setup();

    await supervisor.bestEffort(async () => {
      proc.emit("unhandledRejection", new Error("bank sync noise"));
    });
    await flush();

    expect(onFatal).not.toHaveBeenCalled();
    expect(exit).not.toHaveBeenCalled();
    const logged = log.mock.calls.map((c) => c.join(" ")).join("\n");
    expect(logged).toContain("bank sync noise");
  });

  it("suppresses a background rejection that surfaces just after the work resolves", async () => {
    const { proc, exit, onFatal, supervisor } = setup();

    await supervisor.bestEffort(async () => {
      setImmediate(() => proc.emit("unhandledRejection", new Error("out-of-band")));
    });
    await flush();

    expect(onFatal).not.toHaveBeenCalled();
    expect(exit).not.toHaveBeenCalled();
  });

  it("returns the wrapped function's value and resumes treating rejections as fatal afterward", async () => {
    const { proc, exit, onFatal, supervisor } = setup();

    const value = await supervisor.bestEffort(async () => 42);
    expect(value).toBe(42);

    proc.emit("unhandledRejection", new Error("after the window"));
    await flush();
    expect(onFatal).toHaveBeenCalledTimes(1);
    expect(exit).toHaveBeenCalledWith(1);
  });
});

describe("createSupervisor — dispose", () => {
  it("removes its process listeners", () => {
    const { proc, supervisor } = setup();
    expect(proc.listenerCount("unhandledRejection")).toBe(1);
    expect(proc.listenerCount("uncaughtException")).toBe(1);

    supervisor.dispose();

    expect(proc.listenerCount("unhandledRejection")).toBe(0);
    expect(proc.listenerCount("uncaughtException")).toBe(0);
  });
});
