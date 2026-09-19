function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing required env var ${name}`);
  return v;
}

function csv(v) {
  return v
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function intOr(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  if (!/^-?\d+$/.test(raw.trim())) throw new Error(`env var ${name} must be an integer, got '${raw}'`);
  return Number.parseInt(raw, 10);
}

function positiveInt(name, fallback) {
  const value = intOr(name, fallback);
  if (value < 1) throw new Error(`${name} must be positive`);
  return value;
}

function nonNegativeInt(name, fallback) {
  const value = intOr(name, fallback);
  if (!Number.isSafeInteger(value) || value < 0)
    throw new Error(`${name} must be a non-negative safe integer`);
  return value;
}

function publicBudgetUrl() {
  const value = required("BEHOLDER_BUDGET_URL");
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error("BEHOLDER_BUDGET_URL must be an HTTP or HTTPS URL");
  }
  if (!["http:", "https:"].includes(url.protocol)) {
    throw new Error("BEHOLDER_BUDGET_URL must be an HTTP or HTTPS URL");
  }
  return value;
}

export function loadConfig({ preview = false, previewTo = "" } = {}) {
  const mailRequired = !preview || csv(previewTo).length > 0;
  return {
    actual: {
      serverUrl: required("ACTUAL_SERVER_URL"),
      password: required("ACTUAL_PASSWORD"),
      syncId: required("ACTUAL_BUDGET_SYNC_ID"),
      dataDir: process.env.BEHOLDER_DATA_DIR || "/state/actual-data",
    },
    // Household names, resolved to ids against the budget server at startup.
    names: {
      checking: required("BEHOLDER_CHECKING_ACCOUNT"),
      cards: csv(required("BEHOLDER_CARD_ACCOUNTS")),
      savingsCategory: required("BEHOLDER_SAVINGS_CATEGORY"),
    },
    budgetUrl: publicBudgetUrl(),
    postalUrl: mailRequired ? required("BEHOLDER_POSTAL_URL") : "",
    postalApiKey: mailRequired ? required("BEHOLDER_POSTAL_API_KEY") : "",
    alertFrom: process.env.BEHOLDER_ALERT_FROM || "budget@example.dev",
    alertTo: csv(preview ? previewTo : required("BEHOLDER_ALERT_TO")),
    runAt: process.env.BEHOLDER_RUN_AT || "07:00",
    driftThresholdCents: intOr("BEHOLDER_DRIFT_THRESHOLD_CENTS", 20000),
    duplicates: {
      lookbackDays: positiveInt("BEHOLDER_DUPLICATE_LOOKBACK_DAYS", 90),
      windowDays: positiveInt("BEHOLDER_DUPLICATE_WINDOW_DAYS", 3),
      maxIncreasePercent: nonNegativeInt("BEHOLDER_DUPLICATE_MAX_INCREASE_PERCENT", 30),
      holdMaxCents: nonNegativeInt("BEHOLDER_DUPLICATE_HOLD_MAX_CENTS", 100),
    },
    statePath: process.env.BEHOLDER_STATE_PATH || "/state/beholder.json",
  };
}
