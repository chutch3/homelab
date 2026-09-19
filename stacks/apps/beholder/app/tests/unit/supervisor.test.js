import { describe, expect, it, vi } from "vitest";
import { createSupervisor } from "../../src/supervisor.js";

function subject({ onFatal = vi.fn(async () => {}), settle = async () => {} } = {}) {
  const listeners = new Map();
  const proc = {
    on: (event, fn) => listeners.set(event, fn),
    removeListener: (event, fn) => {
      if (listeners.get(event) === fn) listeners.delete(event);
    },
  };
  const exit = vi.fn();
  const log = vi.fn();
  const supervisor = createSupervisor({ proc, onFatal, exit, log, settle });
  return { supervisor, listeners, exit, log, onFatal, emit: (event, error) => listeners.get(event)(error) };
}
describe("supervisor decisions", () => {
  it.each(["unhandledRejection", "uncaughtException"])("reports %s and exits once", async (event) => {
    const s = subject();
    const error = new Error("fatal");
    await s.emit(event, error);
    expect(s.onFatal).toHaveBeenCalledExactlyOnceWith(error);
    expect(s.exit).toHaveBeenCalledExactlyOnceWith(1);
  });
  it("waits for the reporter before exiting", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const s = subject({ onFatal: vi.fn(() => pending) });
    const error = new Error("fatal");
    const handling = s.emit("unhandledRejection", error);
    expect(s.onFatal).toHaveBeenCalledExactlyOnceWith(error);
    expect(s.exit).not.toHaveBeenCalled();
    release();
    await handling;
    expect(s.exit).toHaveBeenCalledExactlyOnceWith(1);
  });
  it("exits even if reporting fails", async () => {
    const s = subject({
      onFatal: vi.fn(async () => {
        throw new Error("postal down");
      }),
    });
    await s.emit("uncaughtException", new Error("fatal"));
    expect(s.exit).toHaveBeenCalledExactlyOnceWith(1);
  });
  it("handles concurrent fatal events only once", async () => {
    const s = subject();
    const first = new Error("first");
    await Promise.all([
      s.emit("unhandledRejection", first),
      s.emit("uncaughtException", new Error("second")),
    ]);
    expect(s.onFatal).toHaveBeenCalledExactlyOnceWith(first);
    expect(s.exit).toHaveBeenCalledExactlyOnceWith(1);
  });
  it("suppresses errors during work and returns its value", async () => {
    const s = subject();
    expect(
      await s.supervisor.bestEffort(async () => {
        await s.emit("unhandledRejection", new Error("noise"));
        return 42;
      }),
    ).toBe(42);
    expect(s.log).toHaveBeenCalledExactlyOnceWith(
      "[beholder] ignored async error during best-effort work: noise",
    );
    expect(s.onFatal).not.toHaveBeenCalled();
    expect(s.exit).not.toHaveBeenCalled();
  });
  it("keeps suppression through the injected background wait then restores fatal handling", async () => {
    let s;
    const settle = vi.fn(async () => {
      await s.emit("unhandledRejection", new Error("late noise"));
    });
    s = subject({ settle });
    await s.supervisor.bestEffort(async () => 42);
    expect(settle).toHaveBeenCalledExactlyOnceWith();
    expect(s.onFatal).not.toHaveBeenCalled();
    expect(s.exit).not.toHaveBeenCalled();
    const error = new Error("after");
    await s.emit("unhandledRejection", error);
    expect(s.onFatal).toHaveBeenCalledExactlyOnceWith(error);
    expect(s.exit).toHaveBeenCalledExactlyOnceWith(1);
  });
  it("restores fatal handling after wrapped work rejects", async () => {
    const s = subject();
    const error = new Error("work failed");
    await expect(
      s.supervisor.bestEffort(async () => {
        throw error;
      }),
    ).rejects.toBe(error);
    await s.emit("unhandledRejection", error);
    expect(s.exit).toHaveBeenCalledExactlyOnceWith(1);
  });
  it("removes both registered listeners on disposal", () => {
    const s = subject();
    expect([...s.listeners.keys()]).toEqual(["unhandledRejection", "uncaughtException"]);
    s.supervisor.dispose();
    expect([...s.listeners.keys()]).toEqual([]);
  });
});
