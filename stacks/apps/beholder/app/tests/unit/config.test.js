import { afterEach, describe, expect, it, vi } from "vitest";
import { loadConfig } from "../../src/config.js";

// Env stubbing is the unavoidable global-state exception; everything else
// asserts through loadConfig's returned structure.

const VALID = {
  ACTUAL_SERVER_URL: "http://actual.test:5006",
  ACTUAL_PASSWORD: "pw",
  ACTUAL_BUDGET_SYNC_ID: "sync-id",
  BEHOLDER_POSTAL_URL: "http://postal.test:5000",
  BEHOLDER_POSTAL_API_KEY: "key",
  BEHOLDER_ALERT_TO: "a@test.dev, b@test.dev",
  BEHOLDER_CHECKING_ACCOUNT: "Chase Checking",
  BEHOLDER_CARD_ACCOUNTS: "Discover, Southwest Credit Card,",
  BEHOLDER_SAVINGS_CATEGORY: "Wealthfront",
};

function stubEnv(overrides = {}) {
  const env = { ...VALID, ...overrides };
  for (const [k, v] of Object.entries(env)) {
    if (v === undefined) vi.stubEnv(k, "");
    else vi.stubEnv(k, v);
  }
}

afterEach(() => vi.unstubAllEnvs());

describe("loadConfig", () => {
  it("builds the full config from a valid environment", () => {
    stubEnv();
    const c = loadConfig();
    expect(c.actual.serverUrl).toBe("http://actual.test:5006");
    expect(c.names).toEqual({
      checking: "Chase Checking",
      cards: ["Discover", "Southwest Credit Card"],
      savingsCategory: "Wealthfront",
    });
    expect(c.alertTo).toEqual(["a@test.dev", "b@test.dev"]);
    expect(c.driftThresholdCents).toBe(20000);
    expect(c.runAt).toBe("07:00");
  });

  it("trims and drops empty entries in comma lists", () => {
    stubEnv({ BEHOLDER_ALERT_TO: " x@test.dev ,, y@test.dev ," });
    expect(loadConfig().alertTo).toEqual(["x@test.dev", "y@test.dev"]);
  });

  it("names the missing variable when required config is absent", () => {
    stubEnv({ BEHOLDER_POSTAL_API_KEY: undefined });
    expect(() => loadConfig()).toThrow(/BEHOLDER_POSTAL_API_KEY/);
  });

  it("accepts a valid integer threshold override", () => {
    stubEnv({ BEHOLDER_DRIFT_THRESHOLD_CENTS: "50000" });
    expect(loadConfig().driftThresholdCents).toBe(50000);
  });

  it("rejects non-numeric threshold values", () => {
    stubEnv({ BEHOLDER_DRIFT_THRESHOLD_CENTS: "banana" });
    expect(() => loadConfig()).toThrow(/BEHOLDER_DRIFT_THRESHOLD_CENTS/);
  });

  it("rejects partially-numeric garbage instead of silently truncating", () => {
    stubEnv({ BEHOLDER_DRIFT_THRESHOLD_CENTS: "123banana" });
    expect(() => loadConfig()).toThrow(/BEHOLDER_DRIFT_THRESHOLD_CENTS/);
  });
});
