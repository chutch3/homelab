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

export function loadConfig() {
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
    postalUrl: required("BEHOLDER_POSTAL_URL"),
    postalApiKey: required("BEHOLDER_POSTAL_API_KEY"),
    alertFrom: process.env.BEHOLDER_ALERT_FROM || "budget@example.dev",
    alertTo: csv(required("BEHOLDER_ALERT_TO")),
    runAt: process.env.BEHOLDER_RUN_AT || "07:00",
    driftThresholdCents: intOr("BEHOLDER_DRIFT_THRESHOLD_CENTS", 20000),
    statePath: process.env.BEHOLDER_STATE_PATH || "/state/beholder.json",
  };
}
