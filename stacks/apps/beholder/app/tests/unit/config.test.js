import { afterEach, describe, expect, it, vi } from "vitest";
import { loadConfig } from "../../src/config.js";

// Env stubbing is the unavoidable global-state exception; everything else
// asserts through loadConfig's returned structure.

const VALID = {
  ACTUAL_SERVER_URL: "http://actual.test:5006",
  ACTUAL_PASSWORD: "pw",
  BEHOLDER_BUDGET_URL: "https://budget.test/",
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
  it.each([
    [50, 500],
    [0, 0],
  ])("reads duplicate amount thresholds %s / %s", (percent, cents) => {
    stubEnv({
      BEHOLDER_DUPLICATE_MAX_INCREASE_PERCENT: String(percent),
      BEHOLDER_DUPLICATE_HOLD_MAX_CENTS: String(cents),
    });
    expect(loadConfig().duplicates.maxIncreasePercent).toBe(percent);
    expect(loadConfig().duplicates.holdMaxCents).toBe(cents);
  });
  for (const name of ["BEHOLDER_DUPLICATE_MAX_INCREASE_PERCENT", "BEHOLDER_DUPLICATE_HOLD_MAX_CENTS"]) {
    it.each(["-1", "1.5", "bad", "9007199254740992"])(`rejects invalid ${name}: %s`, (value) => {
      stubEnv({ [name]: value });
      expect(() => loadConfig()).toThrow(name);
    });
  }

  it("defaults duplicate review to 90 days and a three-day matching window", () => {
    stubEnv({ BEHOLDER_DUPLICATE_LOOKBACK_DAYS: "", BEHOLDER_DUPLICATE_WINDOW_DAYS: "" });
    expect(loadConfig().duplicates).toEqual({
      lookbackDays: 90,
      windowDays: 3,
      maxIncreasePercent: 30,
      holdMaxCents: 100,
    });
  });
  it("accepts duplicate review window overrides", () => {
    stubEnv({ BEHOLDER_DUPLICATE_LOOKBACK_DAYS: "30", BEHOLDER_DUPLICATE_WINDOW_DAYS: "2" });
    expect(loadConfig().duplicates).toEqual({
      lookbackDays: 30,
      windowDays: 2,
      maxIncreasePercent: 30,
      holdMaxCents: 100,
    });
  });
  it.each(["0", "-1", "1.5", "bad"])("rejects invalid duplicate lookback %s", (value) => {
    stubEnv({ BEHOLDER_DUPLICATE_LOOKBACK_DAYS: value });
    expect(() => loadConfig()).toThrow(/BEHOLDER_DUPLICATE_LOOKBACK_DAYS/);
  });
  it.each(["0", "-1", "1.5", "bad"])("rejects invalid duplicate matching window %s", (value) => {
    stubEnv({ BEHOLDER_DUPLICATE_WINDOW_DAYS: value });
    expect(() => loadConfig()).toThrow(/BEHOLDER_DUPLICATE_WINDOW_DAYS/);
  });

  it("allows a file preview without mail credentials", () => {
    stubEnv({ BEHOLDER_POSTAL_URL: "", BEHOLDER_POSTAL_API_KEY: "", BEHOLDER_ALERT_TO: "" });
    const config = loadConfig({ preview: true });
    expect(config.alertTo).toEqual([]);
    expect(config.actual.serverUrl).toBe(VALID.ACTUAL_SERVER_URL);
  });

  it("requires mail credentials when a preview recipient is selected", () => {
    stubEnv({ BEHOLDER_POSTAL_API_KEY: "" });
    expect(() => loadConfig({ preview: true, previewTo: "preview@test.dev" })).toThrow(
      /BEHOLDER_POSTAL_API_KEY/,
    );
  });

  it("uses only the explicit preview recipients", () => {
    stubEnv();
    expect(loadConfig({ preview: true, previewTo: " preview@test.dev " }).alertTo).toEqual([
      "preview@test.dev",
    ]);
  });

  it("reads the public budget URL from the environment", () => {
    stubEnv();
    expect(loadConfig().budgetUrl).toBe("https://budget.test/");
  });

  it.each(["", "javascript:alert(1)", "not a URL"])("rejects invalid budget URL %s", (url) => {
    stubEnv({ BEHOLDER_BUDGET_URL: url });
    expect(() => loadConfig()).toThrow(/BEHOLDER_BUDGET_URL/);
  });

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
