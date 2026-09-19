import { describe, expect, it } from "vitest";
import { createMetricsRecorder } from "../../src/metrics.js";

function subject() {
  const writes = [];
  const increments = [];
  const recorder = createMetricsRecorder({
    set: (name, value, labels) => writes.push([name, value, labels]),
    increment: (name, labels) => increments.push([name, labels]),
  });
  return { recorder, writes, increments };
}
const zeroFindings = ["floor", "raid", "drift", "schedule", "uncategorized", "duplicates"].map((check) => [
  "findings",
  0,
  { check },
]);
describe("metrics recording", () => {
  it("initializes every check to zero", () => {
    const { writes, increments } = subject();
    expect(writes).toEqual(zeroFindings);
    expect(increments).toEqual([]);
  });
  it("records success with exact counts, timestamp and duration", () => {
    const { recorder, writes, increments } = subject();
    recorder.recordRun({
      findings: [{ check: "floor" }, { check: "drift" }, { check: "drift" }],
      durationSeconds: 2.5,
      now: 1700000000,
    });
    expect(writes.slice(6)).toEqual([
      ["lastRunTimestamp", 1700000000, undefined],
      ["lastRunSuccess", 1, undefined],
      ["runDuration", 2.5, undefined],
      ["findings", 1, { check: "floor" }],
      ["findings", 0, { check: "raid" }],
      ["findings", 2, { check: "drift" }],
      ["findings", 0, { check: "schedule" }],
      ["findings", 0, { check: "uncategorized" }],
      ["findings", 0, { check: "duplicates" }],
    ]);
    expect(increments).toEqual([["runsTotal", { outcome: "success" }]]);
  });
  it("records failure without rewriting the previous findings", () => {
    const { recorder, writes, increments } = subject();
    recorder.recordFailure({ now: 1700000500 });
    expect(writes.slice(6)).toEqual([
      ["lastRunTimestamp", 1700000500, undefined],
      ["lastRunSuccess", 0, undefined],
    ]);
    expect(increments).toEqual([["runsTotal", { outcome: "failure" }]]);
  });
  it("resets counts on the next empty run and ignores unknown checks", () => {
    const { recorder, writes } = subject();
    recorder.recordRun({ findings: [{ check: "floor" }], durationSeconds: 1, now: 1 });
    recorder.recordRun({ findings: [{ check: "unknown" }], durationSeconds: 2, now: 2 });
    expect(writes.slice(-6)).toEqual(zeroFindings);
  });
});
