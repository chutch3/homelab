# beholder

Budget watchdog. Once a day it reads the household budget from the Actual
server and runs four checks; if anything is wrong it sends one email through
Postal (`budget@${BASE_DOMAIN}`) to everyone in `BEHOLDER_ALERT_TO`.
**Quiet by default — no email means all checks passed.**

## The checks

| Check | Fires when |
| --- | --- |
| floor | checking holds less than the credit cards currently owe |
| raid | money flowed OUT of the savings category (deliberate irregulars get recategorized to their event category and stop alerting) |
| drift | a card's debt is more than `$200` higher than ~30 days ago |
| schedule | a payee with an active exact-amount schedule posted, and nothing matched the promised amount (extra payments are fine; $119 instead of $200 is not) |
| uncategorized | transactions on open on-budget accounts with no category (transfers excluded — card payments are legitimately uncategorized) |

Each run triggers a bank sync first (best effort — a sync failure warns and
the checks run on last-synced data). Event findings (raid, schedule,
uncategorized) alert exactly once per transaction; condition findings
(floor, drift) repeat daily until resolved.

No household facts live in source. Account and category *names* come from
`.env` and are resolved to ids against the budget server at startup —
unresolvable names fail the run loudly with the list of what exists.
Watched schedules are read from the budget server itself: change a schedule
in Actual and beholder follows automatically.

## Deploying

`.env` needs, alongside the existing `ACTUAL_*` vars:

| Var | Example |
| --- | --- |
| `BEHOLDER_ALERT_TO` | comma-separated recipients |
| `BEHOLDER_POSTAL_API_KEY` | API credential minted in Postal for this app |
| `BEHOLDER_CHECKING_ACCOUNT` | the checking account's name in Actual |
| `BEHOLDER_CARD_ACCOUNTS` | comma-separated card account names (floor + drift scope) |
| `BEHOLDER_SAVINGS_CATEGORY` | the savings category name (raid scope) |

Verify a deploy end to end by forcing an immediate run:

```sh
docker exec -e BEHOLDER_RUN_ONCE=1 $(docker ps -qf name=beholder) node src/index.js
```

Exit 0 and a `run complete` log line = the full pipeline works. It prints
`(quiet)` when there is nothing to report.

## Development

```sh
cd app && npm install
npm test              # everything
npm run test:unit     # fast tier only
npm run test:integration
```

Two tiers, warden-harness style, no middle layer:

- **Unit** (`tests/unit/`) — one test file per module, every owned seam
  injected. All exact arithmetic lives here. Fast, no I/O.
- **Integration** (`tests/integration/`) — beholder launched as a real
  subprocess (the Dockerfile CMD with `BEHOLDER_RUN_ONCE=1`) against a REAL
  `@actual-app/sync-server` booted on a temp dir and seeded with fixture
  budgets, plus mockttp standing in for Postal (a real server on a real port — unmatched requests fail loudly). Observed only through
  real surfaces: exit code, the fake's captured requests, stdout, the state
  file. The harness never imports `src/`.

Spec and plan: `docs/superpowers/` (not committed).

## Companion

The monthly narrative report (budget grades, saved-vs-dipped, buffer
glidepath) is a separate scheduled Claude session, not part of this service.
