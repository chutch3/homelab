import { describe, expect, it } from "vitest";
import { msUntilNextRun, scheduleDaily } from "../../src/run.js";

describe("daily scheduling", () => {
  it.each([
    [new Date(2026, 8, 10, 6, 59), 60000],
    [new Date(2026, 8, 10, 7, 0), 86400000],
    [new Date(2026, 8, 10, 7, 1), 86340000],
    [new Date(2026, 11, 31, 23, 59), 25260000],
  ])("schedules the next local 07:00 after %s", (now, expected) => {
    expect(msUntilNextRun("07:00", now)).toBe(expected);
  });
  it("waits for each run and schedules again after a reported failure", async () => {
    const scheduled = [];
    const failures = [];
    let runs = 0;
    let release;
    const gate = new Promise((resolve) => {
      release = resolve;
    });
    scheduleDaily({
      runAt: "07:00",
      now: () => new Date(2026, 8, 10, 6, 59),
      schedule: (callback, delay) => scheduled.push({ callback, delay }),
      execute: async () => {
        runs++;
        if (runs === 1) {
          await gate;
          throw new Error("run failed");
        }
      },
      onError: async (error) => failures.push(error.message),
    });
    expect(runs).toBe(0);
    expect(scheduled.map((s) => s.delay)).toEqual([60000]);
    const first = scheduled[0].callback();
    expect(runs).toBe(1);
    expect(scheduled).toHaveLength(1);
    release();
    await first;
    expect(failures).toEqual(["run failed"]);
    expect(scheduled.map((s) => s.delay)).toEqual([60000, 60000]);
    await scheduled[1].callback();
    expect(runs).toBe(2);
    expect(scheduled).toHaveLength(3);
  });
});
