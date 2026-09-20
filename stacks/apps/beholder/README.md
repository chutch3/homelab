# beholder

Budget watchdog. Once a day it reads the household budget from the Actual
server and runs six checks. Every successful run sends one HTML email with
plain-text fallback through Postal (`budget@${BASE_DOMAIN}`) to everyone in
`BEHOLDER_ALERT_TO`, including days with no new findings.

## The daily update

The email uses Actual Budget's default dark palette: near-black page background,
navy tables, pale text, purple accents, and light red overspending amounts.
Styles are inline, with dark color-scheme metadata; individual mail clients may
still adjust colors. This is a fixed email theme, independent of browser preferences.

The email begins with **visible spending categories** and their remaining
balances for the current month. Hidden categories, categories in hidden groups,
and income categories are excluded. Balances come directly from Actual and
include carried-over funds. All categories stay in alphabetical order for quick
lookup. Each row emphasizes the remaining amount (or amount over budget), with
a slim spending bar and smaller spending/available figures underneath.
Available funds are the remaining balance minus Actual's signed monthly activity;
spending is net of refunds. Bars cap at 100%, while overspending remains explicit
in red text and numbers. Zero-funded categories and net inflows have explicit labels. The budget month and
email date use the container timezone (`TZ`).

An uncategorized-transaction notice appears above the balances when needed,
with spending and inflows shown separately. It covers the existing 14-day
lookback, not the entire backlog. Unresolved transactions remain visible in
subsequent daily updates within that window, even after their finding has
already been reported.

A monthly spending summary at the top compares total spending with the sum of
this month’s configured budgets for visible spending categories, excluding carryover.
The Open budget link appears above categories. Account balances follow. Savings transactions and payment differences each have a purpose
statement and a table, with totals/differences emphasized. Zero-balance cards show
$0.00 without an owed label. The categorization notice appears only at the top;
there is no generic Items to review section. Dated card-debt changes remain visible. The full current card balance is not the next payment due; payment timing
can affect the balance change. Savings and scheduled-payment findings retain
their details. The email links to Actual and puts transaction details last.
No budget categories or transactions are changed by the report.

## The checks

| Check | Fires when |
| --- | --- |
| floor | checking holds less than the credit cards currently owe |
| raid | positive transactions were assigned to the configured savings category; reported as inflows without assuming their source |
| drift | a card's debt is more than `$200` higher than ~30 days ago |
| schedule | a payee with an active exact-amount schedule posted, and nothing matched the promised amount (extra payments are fine; $119 instead of $200 is not) |
| uncategorized | transactions on open on-budget accounts with no category (transfers excluded — card payments are legitimately uncategorized) |
| duplicates | an imported pending charge has one likely posted replacement with a different imported ID |

Each run triggers a bank sync first (best effort — a sync failure warns and
the checks run on last-synced data). Event findings (raid, schedule,
uncategorized) retain the existing deduplication keys and are marked reported
only after successful delivery; condition findings (floor, drift, duplicates) repeat daily
until resolved. Unresolved uncategorized transactions also appear as daily
context, without being counted as new findings again. A failed run attempts a
separate failure email rather than sending an incomplete budget summary.

No household facts live in source. Account and category *names* come from
`.env` and are resolved to ids against the budget server at startup —
unresolvable names fail the run loudly with the list of what exists.
Watched schedules are read from the budget server itself: change a schedule
in Actual and beholder follows automatically.

## Possible duplicate charges

The email shows each candidate as a pending/posted pair with account, merchant,
dates, and amounts. Check these against the bank before removing anything in
Actual; Beholder never merges or deletes transactions.

The check scans 90 days of imported spending on open, on-budget accounts,
excluding transfers and split transactions. It pairs an uncleared entry with a
cleared entry on the same account, with different imported IDs and dates within
three days. Merchant names must match after case/punctuation normalization, or
share a complete prefix of at least two words (for example, “Coast Creamery” and
“Coast Creamery Santa Rosa”). It does not treat “Kroger” and “Kroger Fuel” as a match.

The posted amount must be higher: by default, either the pending amount is at most
$1, or the increase is at most 30%. Both thresholds are configurable. Multiple
possible matches are omitted rather than
choosing one. This deliberately misses some duplicates, including equal or lower
final amounts. Cleared status is evidence for review, not proof of a duplicate.
Candidates repeat while both entries qualify within the lookback.

Optional environment settings, also passed through by the stack:

| Variable | Default | Meaning |
| --- | --- | --- |
| `BEHOLDER_DUPLICATE_LOOKBACK_DAYS` | `90` | Transaction history to inspect |
| `BEHOLDER_DUPLICATE_WINDOW_DAYS` | `3` | Maximum difference between the two transaction dates |
| `BEHOLDER_DUPLICATE_MAX_INCREASE_PERCENT` | `30` | Maximum increase over the pending amount, unless it qualifies as a small hold |
| `BEHOLDER_DUPLICATE_HOLD_MAX_CENTS` | `100` | Largest pending amount treated as a small hold, allowing any higher posted amount |

Day settings must be positive integers. Amount thresholds must be non-negative
safe integers. Set `BEHOLDER_DUPLICATE_HOLD_MAX_CENTS=0` to disable the small-hold
exception. Setting the percentage to `0` leaves only small-hold matches; setting
both thresholds to `0` produces no candidates.

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
`daily update sent` when there are no new findings.

The stack supplies `BEHOLDER_BUDGET_URL=https://budget.${BASE_DOMAIN}` for the
**Open budget** link. When running outside the stack, set `BEHOLDER_BUDGET_URL`
to your public Actual HTTP(S) address; the internal `ACTUAL_SERVER_URL` is for
API access, not browser navigation. The existing run time, timezone, recipients,
and account settings are unchanged. No additional service or dependency is needed.

## Local preview

From the repository root, using Node 22+ and the existing `.env`:

```sh
npm --prefix stacks/apps/beholder/app ci  # first use
task beholder:preview
```

Open `/tmp/beholder-preview.html` in your browser. The task runs the current
checkout, downloads the budget and attempts bank sync; no image build,
deployment, or Swarm node access is needed. If bank sync fails, it uses the
last synced budget. A temporary Actual cache is removed when the run finishes.

To choose the output location or send that exact HTML to a test recipient:

```sh
task beholder:preview OUTPUT=/tmp/my-budget.html
task beholder:preview TO=you@example.com
```

Sending is opt-in through `TO`; the normal household recipient list is ignored.
HTML-only previews do not require Postal credentials. Sending requires the
existing Postal API key. The generated file contains your budget information.

The task loads the root `.env` and defaults API access and the budget link to
`https://budget.${BASE_DOMAIN}`, Postal to `https://postal.${BASE_DOMAIN}`, and
sender to `budget@${BASE_DOMAIN}`. Explicit `ACTUAL_SERVER_URL`,
`BEHOLDER_BUDGET_URL`, `BEHOLDER_POSTAL_URL`, and `BEHOLDER_ALERT_FROM` override
these defaults. Actual credentials, account names, timezone, and drift threshold
use the existing environment settings. Your machine must be able to reach Actual
(and Postal if sending).

Preview runs never save snapshots or notification history. By default they have
no historical card-debt comparison and treat current event findings as new.
Optionally set `BEHOLDER_STATE_PATH` to a **local copy** of Beholder's history
file to include its baseline and deduplication context; the file is read only.

Without Task, set `BEHOLDER_PREVIEW_OUTPUT` to the output filename and run
`node src/index.js` from `app/` with the required environment loaded. Set
`BEHOLDER_PREVIEW_TO` only when sending is desired.

### Editing the email

Email content lives in `app/src/email/templates/`:

- `report.html.hbs`: section order, HTML layout, table columns, and styles.
- `report.text.hbs`: the plain-text version of the report.
- `partials/layout.hbs`: the shared page frame, header, and footer.
- Other partials share the subject, notices, balance labels, and progress bars.

Templates receive numeric balances, calculated activity, accounts, and findings
from `run.js`. They own wording, formatting, sorting, and simple display
conditions. For example:

```handlebars
{{#each (sortByName categories)}}
  <p>{{name}}: {{money (abs balance)}} {{#if (negative balance)}}over{{else}}left{{/if}}</p>
{{/each}}
```

Formatting helpers live in `app/src/email/helpers.js`; financial calculations
remain in `app/src/money.js`. HTML expressions escape values automatically.
Use normal `{{expressions}}` for report data, without raw HTML expressions.

Run `task beholder:preview` again after editing and refresh the generated file.
Compiled templates are reused within a running process; a new preview process
loads the edited files. Deployed template changes require rebuilding and
redeploying the application. Update both report templates for wording that
is not already in a shared partial.

### Actual version compatibility

Beholder pins `@actual-app/api` to 26.9.0. The integration server remains on
26.5.2 to verify compatibility with older sync servers. Regressions cover both
a snapshot migrated by 26.7.0 and account-group sync messages introduced in
26.9.0: another Actual client can write newer schema data independently of the
sync server version.

If preview reports `out-of-sync-migrations` or `invalid-schema` with a missing
column such as `account_group_id`, the installed API may be too old for the
budget snapshot or sync updates. After pulling dependency updates, run
`npm --prefix stacks/apps/beholder/app ci` from the repository root and retry.
Do not remove migration records from the budget to make an older client load it.

## Postal integration

Alert mail goes through Postal's HTTP API at `https://postal.${BASE_DOMAIN}`
(`BEHOLDER_POSTAL_URL` in `docker-compose.yml`). It must be the traefik
hostname, **not** the internal `postal_web:5000` service address: Postal
enforces Rails host authorization on `POSTAL_WEB_HOSTNAME`, so a request
carrying any other `Host` header is rejected with a blank `403` and no mail
leaves — silently, since the body is empty. A `postal send failed: HTTP 403 {}`
line in a run is that host mismatch, not a bad key. (The internal address can't
be salvaged with a `Host` override either: `fetch`/undici ignores a manual
`Host` header.)

`BEHOLDER_POSTAL_API_KEY` is a Postal API credential; the mail server must be
Live and the sending domain (`${BASE_DOMAIN}`) verified.

## Development

```sh
cd app && npm ci
npx playwright install --with-deps chromium  # browser integration tests
npm test              # everything
npm run test:unit     # fast tier only
npm run test:integration
```

Two tiers, warden-harness style, no middle layer:

- **Unit** (`tests/unit/`) — one test file per module, every owned seam
  injected. All exact arithmetic lives here. Fast, no I/O.
- **Integration** (`tests/integration/beholder.e2e.test.js`) — the single suite
  for component collaboration, including success and failure paths. Beholder runs as a real
  subprocess (the Dockerfile CMD with `BEHOLDER_RUN_ONCE=1`) against a REAL
  `@actual-app/sync-server` booted on a temp dir and seeded with fixture
  budgets, plus mockttp standing in for Postal (a real server on a real port — unmatched requests fail loudly). Observed only through
  real surfaces: exit code, the fake's captured requests, stdout, the state
  file. Browser checks render the delivered email at phone and desktop widths.
  Every application scenario starts `node src/index.js`, configured through
  environment variables. Tests observe its external outputs; they do not invoke
  Taskfile commands or import application internals. Supervisor decisions are
  covered separately by isolated unit tests.

Spec and plan: `docs/superpowers/` (not committed).

## Companion

The monthly narrative report (budget grades, saved-vs-dipped, buffer
glidepath) is a separate scheduled Claude session, not part of this service.
