# DiskTracker

The first local implementation supports manually recorded prices for offers (one store selling one MPN in one condition), exact pre-tax totals and $/TB, a dated price history, and the change between each offer's two most recent totals. Every price has an item price; shipping & fees is one optional amount that counts as $0 when blank, so every total and $/TB is known. Listings that share an MPN automatically link to one shared Drive record, so specifications are entered once and every listing for that drive shows the same values; the primary table shows one row per drive with its cheapest current listing surfaced, and opens to one Offers row per seller with the lowest price marked, a combined price trend, and collapsed price history. Saves are transactional and retries replay the original result. Backdated entries do not replace newer observations.

This is a development slice, not the complete planned application. Comparison selection, observation invalidation, charts, production packaging/deployment, and collectors for stores other than ServerPartDeals remain to be implemented. Use test data until backup/restore and the private deployment configuration are in place.

## Layout

- `frontend/`: React, TypeScript, Vite, and Mantine. Frontend tests live here.
- `backend/`: FastAPI, SQLAlchemy, Alembic migrations, and backend unit/integration tests. HTTP contracts and their database effects are covered together in `backend/tests/integration/test_api.py`.
- `collector/`: the collectors (ServerPartDeals, goHardDrive, Western Digital), a separate service that posts scraped offers to the API (see [Collector](#collector)).
- `listing_text/`: the readers that find an MPN, capacity, condition, maker and specifications in listing text, shared by the collector and the backend (which uses them to read pasted listings). Both depend on it by local path; `ci projects` re-tests both when it changes.
- `tests/e2e/`: full-application browser tests. These start the frontend and backend against disposable PostgreSQL databases.
- `backend/tests/conftest.py` and `tests/e2e/conftest.py`: independent backend and E2E database fixtures. Each owns its environment override check and Testcontainers lifecycle, creates a unique database per test, and drops only that database afterward.

## Local prerequisites

Use Python 3.12+, Node 22.12+, and uv. Database tests start PostgreSQL 16 through Testcontainers by default, so they need an accessible Docker daemon. Alternatively, supply a dedicated test PostgreSQL instance through `DISKTRACKER_TEST_ADMIN_URL` to run without Docker. The development app still needs its own PostgreSQL instance. Install dependencies from their lockfiles:

```bash
cd stacks/apps/disktracker/backend
uv sync --frozen
uv run playwright install chromium
```

In `frontend/`, run `npm ci`. Playwright's test dependencies currently use the backend virtual environment, but full-application tests and their server/browser fixtures live at the application root.

Set `DISKTRACKER_DATABASE_URL` to a SQLAlchemy PostgreSQL URL (`postgresql+psycopg://...`) for the development database. Optionally set `DISKTRACKER_TEST_ADMIN_URL` to a Psycopg URL (`postgresql://...`) for a dedicated PostgreSQL instance whose role can create/drop test databases. A non-empty value bypasses Testcontainers entirely; a bad connection fails rather than falling back to Docker. Never point the test admin URL at a production database. Credentials are supplied through environment variables and are not committed.

With the test admin URL unset or blank, each suite's own fixture starts one `postgres:16-alpine` container per pytest session, only when a database test requests it, and stops it afterward. Backend and E2E tests do not share their database fixtures or containers. Both modes create, migrate, and drop a unique database per test; neither migrates nor clears an existing database. Tests that do not request the database fixture need no Docker or PostgreSQL. CI uses this automatic mode; its E2E workflow also installs frontend dependencies and Playwright Chromium.

PostgreSQL runs locally per container, one private cluster each. Its data lives on the container's own disk at `${XDG_STATE_HOME:-~/.local/state}/disktracker/postgres`, never on the workspace: the workspace is a cluster filesystem on shared iSCSI storage, where a single write can stall for many seconds (enough to time out browser tests). Credentials are in `stacks/apps/disktracker/.local/env-<hostname>.sh` (mode `0600`); keying them by hostname keeps containers sharing the workspace from reading each other's. `.local/` is ignored and contains only local development state; it is not a deployment configuration.

## Set up local PostgreSQL

On Ubuntu/Debian, run this once per container as your normal user:

```bash
bash stacks/apps/disktracker/scripts/setup-postgres.sh
```

The script installs PostgreSQL 16 if needed (using sudo), initializes a private cluster under `~/.local/state/disktracker/postgres`, starts it on `127.0.0.1:55432`, creates the development database, and saves generated credentials in `.local/env-<hostname>.sh`. An existing setup for this host keeps its data and credentials; rerunning the script starts PostgreSQL if it has stopped. If the credentials exist but the cluster does not (a rebuilt container), it starts a fresh cluster under the same credentials. It refuses to overwrite an incomplete cluster.

Because the cluster is on this container's own disk, a stale PID file means *this container's own* server crashed without cleaning up. If `pg_ctl status` can't see it running, it's safe to remove `~/.local/state/disktracker/postgres/postmaster.pid` and rerun the script. The server log is `server.log` in the same directory.

Then run `task dev -- disktracker` to apply migrations and start the app. The script does not configure automatic startup or change the container image. If the container is replaced, rerun it to create a fresh cluster; `scripts/seed-examples.py` restores example data.

## Run locally

From the repository root:

```bash
task dev -- disktracker
```

The development task applies migrations, then runs FastAPI on loopback port 8000 and Vite on loopback port 5173. Ctrl-C stops both application processes; PostgreSQL remains running. It loads `.local/env-<hostname>.sh` for this container when present, or uses your supplied environment variables. PostgreSQL must already be running. `COLLECTOR=1 task dev -- disktracker` also starts the collector, with its API on loopback port 8100 (`COLLECTOR_PORT`), and tells the backend where it is, so sources can be tested from the Admin page. It is off unless asked for: once started, the collector collects every source that is due, from the live stores; switch off on the Admin page the ones it should leave alone.

Open `http://127.0.0.1:5173` from an environment that can reach this container's loopback interface. A browser on another computer needs port forwarding or a private preview route; this task does not change Swarm routing.

For the code-server preview, set the base path when starting development:

```bash
DISKTRACKER_BASE_PATH=/absproxy/5173/ task dev -- disktracker
```

Open `https://code.diyhub.dev/absproxy/5173/` (with the trailing slash). code-server's `/absproxy/` route preserves the prefix so Vite can serve its scripts, live reload, and API proxy under that path. The `/proxy/` route strips the prefix and should not be used with this configuration.

`DISKTRACKER_BASE_PATH` defaults to `/`. Supply a path beginning and ending with `/`; if you change the UI port, update the proxy path to match it. Restart the development task when changing this environment variable.

To choose different ports or a frontend listener address:

```bash
API_PORT=8001 UI_PORT=5174 UI_HOST=127.0.0.1 task dev -- disktracker
```

The app Taskfile only coordinates local servers and migrations. Development and test commands use the shared repository interface. `task build -- disktracker` builds its two images (see Deployment).

## Deployment

`docker-compose.yml` deploys three services to the swarm, with `task deploy -- disktracker`:

- **disktracker**: the API, which also serves the built frontend (`DISKTRACKER_STATIC_DIR`, set in the image), at `https://disktracker.${BASE_DOMAIN}` behind Authentik; the app has no login of its own. It applies its migrations when it starts. Image: `backend/Dockerfile`.
- **disktracker-collector**: the collection loop and its preview API, one replica, reached only by the web service on the stack's internal network. It fetches browser sources through the standalone flaresolverr stack by service name (`http://flaresolverr:8191`; `DISKTRACKER_FLARESOLVERR_URL` overrides it), which is why the stack requires `flaresolverr`. Image: `collector/Dockerfile`.
- **disktracker-db**: Postgres, on a `database` node, its data under `/mnt/iscsi/app-data/disktracker/postgres`, dumped nightly by Fiber.

Both images build from this directory as their context, since each needs `listing_text/` (and the backend needs `frontend/`). `.env` needs `DISKTRACKER_DB_PASSWORD` (letters and digits: it is written into a database URL); `pre-flight.yml` checks it, makes the data directory, and creates the secret Fiber reads. The images are tagged `latest` until a release has promoted them; pin the version in `docker-compose.yml` then, as the other stacks do.

## Collector

`collector/` reads the sources configured on the Admin page and posts every offer to `POST /api/scraped`, which records it or puts it under Needs matching on the Admin page. Every `COLLECTOR_POLL_SECONDS` (default 60) it asks `GET /api/sources/due` which sources are due, runs the first, and asks again, until nothing is due that it has not run that round. Sources asked to run with Run now come ahead of those whose schedule has fired, so one asked for while another runs goes next, and schedules and other changes on the Admin page apply without a restart. While a run goes on it tells disktracker how far it has got (`PUT /api/collector-activity`, at its start and then at most every 15 seconds), which is what the Admin page shows as running; the answer says whether the run was asked to stop, and a run told to stop ends there, keeps what it posted, skips its rechecks and is reported as stopped rather than failed. A collector asking what is due is between runs, so disktracker then forgets any run it was shown as being in: one cut short by a restart does not go on looking as if it were running; if disktracker cannot say, the round logs `sources_unavailable` and counts as failed. Every run is reported, even one that crashes, so a source is not due again until its schedule next fires. A source whose settings the collector cannot read fails its own run (`run_failed`, `settings: …`) and the others still run. Offers are recorded under the source's store, and its runs under its key. There is one reader per type, each driven by the source's settings:

- **Shopify**: each configured collection's `products.json` feed, with specifications from the product type, tags and title. A SKU's base (up to its first `_`) is taken for a part number when the store keys its SKUs that way, which the collector reads from the feed (at least half the titles name their own SKU base), or when a title names it; a store's own SKU codes are left out. Such SKUs group a drive listed many times under one SKU base (bare, per tray) into one listing, name OEM listings by a sibling's maker MPN, and join OEM part numbers to the drive as aliases. *Every order ships free* records shipping as free. ServerPartDeals is one, with free shipping.
- **Sitemap + product page** (no API): the pages the store's sitemap lists (the sitemap at the *sitemap path*, else the ones robots.txt names, else `/sitemap.xml`; a sitemap index is followed one level, each sitemap it names read once), those whose path matches the *product path pattern* (every page when it is blank), skipping any that name an accessory or a memory module (DDR, DIMM, RAM), and, when most product URLs name a capacity, those that do not; then each page's schema.org price and stock: tags in the markup, else the page's JSON-LD Product. The title is the page's `og:title` (else its `<title>`), which carries no store name; MPN, capacity, condition and specifications come from it; the JSON-LD Product is found alone, in a list, or in the `@graph` of several things a page describes; a title that names no condition takes the one the JSON-LD offer states (`itemCondition`, read by the condition rules); a title with no MPN the collector can read takes the part number the page's JSON-LD states (its `mpn`, or its `sku` when the title has that same text), and the maker the JSON-LD names. A drive of a store brand, or sold as white label ("WL", "White Label", "Major Brand"), has no manufacturer MPN and is sold nowhere else, so its MPN is the store's product code, the last part of its page's path; any other drive whose MPN cannot be read goes to Needs matching. A title without a condition is a new item; a page containing the *free-shipping marker* ships free. A store whose page covers a whole family of drives and carries them as JSON inside a script is read from that data instead, when the source's *Pages that list several products* settings say where it is: a *data pattern* (a regular expression whose group holds the JSON; data handed to `JSON.parse('…')` is unescaped first), the *products path* within it (names apart by dots, `*` for every entry of a list), and which field of each product is its model number, name, price, brand and stock. Each product with a price is an offer at the page's URL, numbered and named as the data has it; its capacity and condition are read from the name. Seagate is one (sitemap path `/sitemap.xml`, product path pattern `^/products/`, data pattern `product_models = JSON\.parse\('(.*?)'\);`, products path `*.skus.*`, fields `modelNo`, `name`, `final_price`, `brand`, `stock_status` = `IN_STOCK`). goHardDrive is one (product path pattern `-p/`, free-shipping marker `Help_FreeShipping`): a full run is about 770 pages, roughly 26 minutes at the site's crawl delay.
- **SAP Commerce**: the sitemap's pages (found as for a sitemap store) matching the *product path pattern*, new ones first, then those whose path says *recertified*; then each SKU's price and stock from the store's OCC API (`{API URL}/{site}/products/{sku}`). Retail drives go by their model number (a recertified SKU's *recertified SKU prefix*, if set, is dropped). A new data-center drive goes by the model number the API gives, with the part number (`0F38352`) sent as an alias; a recertified data-center drive has only its part number, so it joins the new drive through that alias, or stands alone until someone adds it with Add another MPN. Products listed without a price (family placeholders, drives no longer sold) are skipped, and shipping is unknown. Western Digital is one: its robots.txt names an index of every locale's sitemaps, so its sitemap path is set to `/products-sitemap.xml` (internal drives only, prefix `R`); about 250 SKUs, roughly 9 minutes a run. WD's terms allow personal, non-commercial use; publishing its prices would need its permission.

The brand is the maker, not the label: Seagate, Western Digital (HGST and Ultrastar fold into it), Toshiba, Intel, Samsung, Micron, Crucial, Kingston or SanDisk, or a store brand sold under its own name (Avolusion; MaxDigital, also written MDD or MaxDigitalData). Dell and HP labels are not makers, so "DELL / Seagate …" is Seagate and a drive named only by an OEM label has no brand. Shopify sources read it from the title and fall back to the brand tag, sitemap sources from the title, and SAP Commerce sources from the API. disktracker records a brand only for a drive that has none yet.

From titles, every reader reads recording type only when it is stated ("CMR", "SMR", or the spelled-out names), since one product line can ship both. Intended use comes from the maker's product line (IronWolf, WD Red and Toshiba N300 are NAS; SkyHawk, WD Purple and Toshiba S300 are Surveillance; Exos, Ultrastar, Constellation and WD Gold are Enterprise; BarraCuda, WD Blue and Toshiba P300 are Desktop) or from a stated "NAS", "Surveillance", "Enterprise", "Data Center" or "Archive". A bare "Desktop" is ignored because it usually describes an external enclosure. Scraped specifications only fill in values nobody has entered.

After posting, the collector rechecks, on its own product page, every in-stock offer from that store the run did not record: sold out, or a missing page, is marked out of stock.

Sold out is only a stock state. disktracker records no price for a sold-out scraped offer, whatever the store shows then (ServerPartDeals shows a $10,000 placeholder), so the offer keeps the price it last had in stock, shown with *Out of stock*; a drive first seen sold out is not recorded (`ignored`) until it is in stock at a real price. The collector works these out itself, so they are not settings: a sold-out placeholder price, whether SKUs are part numbers, the title prefix, a store's own brands and product codes, which product paths name a capacity, and which pages are recertified. What is left for a store is its type and URL, plus Shopify collections or SAP Commerce's API URL and site; the rest (sitemap path, product path pattern, recertified SKU prefix, free shipping) is optional, under *Advanced*.

A source's pages are fetched directly or, when its *Fetch pages* is *Through a browser*, through FlareSolverr (`FLARESOLVERR_URL`, the homelab's standalone `http://flaresolverr:8191`, not the VPN-routed one in the downloads stack) for stores that answer only browsers. robots.txt is read, and requests are spaced, the same way either way; FlareSolverr returns JSON as Chrome renders it, which the collector reads back. Through the browser the collector cannot identify itself (the store sees Chrome), so use it only where the source's basis allows collecting. A browser source without `FLARESOLVERR_URL` fails its run with a settings error; a page FlareSolverr cannot get fails like any unavailable page, with its reason (`browser: …`).

Every request goes through `collector/polite.py`: directly, it identifies itself as `disktracker-collector`, fetches nothing a site's `robots.txt` disallows, and waits the site's `Crawl-delay` between requests, or `COLLECTOR_MIN_DELAY_SECONDS` (default 2) when that is longer or the site asks for none. A site whose `robots.txt` cannot be read (5xx or unreachable) is not collected that run; no `robots.txt` (404) means no restrictions. A site that refuses the request for `robots.txt` itself (401 or 403) is treated as refusing the collector, and reported as `robots.txt disallows …`. `robots.txt` is read at the start of each run and of each Test, and kept only for it, so a refusal is never remembered: the next run or Test asks again. Each source's permission on the Admin page records what allows collecting from it.

### Inspecting a link

*Add store* takes a **Product link**: a link to one drive at a store not read yet. `POST /api/source-inspections` passes it to the collector's `POST /inspect`, which reads that page and answers with the ways of reading the store that read a drive from it, best first: for each, the kind of source, its settings, why they were chosen (`evidence`), how many offers they read from the page and the first of them; the backend adds what recording that offer would do. *Use these settings* fills the form, with the link as the page Test reads. Nothing is kept.

The page is fetched once and shown to the reader of every kind of source; what makes a store one kind or another, and how its settings are worked out, is each reader's own (`Reader.inspect`, beside how it reads settings, offers and rechecks, in its file under `collector/sources/`). Adding a kind of source is adding a reader there and naming it in `container.py`: nothing else in the collector knows the kinds apart.

### Kinds of source

A kind of source is one file under `collector/sources/`: a reader. Its settings are written once, as the fields of a dataclass (`collector/settings.py`), which is both what the kind is described as having (`description`) and how a store's saved settings are read (`settings`). It reads a store's offers (`offers`), just enough of them to try its settings (`sample`), and known offers again, a page several share fetched once (`recheck`); and it tells a store of its kind from one of its pages (`inspect`). A reader that can read one page alone (`page_offers`) can be tested on one; whether it can is not declared but seen. Nothing else names the kinds the collector reads:

- `scripts/generate-source-kinds.sh` writes the readers' descriptions to `backend/disktracker/source_kinds.json` (`--check`, run by pre-commit, fails when that file is stale), so the backend needs no collector running to know them.
- The backend checks a store's settings against its kind's description (`disktracker/kinds.py`): required, a list or a flag, a pattern a text must match, a text that must be a regular expression (with a group), a setting needed once another is given. It serves the descriptions at `GET /api/source-kinds`, with `manual`, a store entered by hand, which is the backend's own kind.
- The Admin form asks for whatever the chosen kind is described as having: required settings at once, the rest under Advanced, grouped as described; *Page to test* for a kind whose reader can read one page alone.

To add a kind: write its reader, name it in `collector/container.py`, and run `task source-kinds`.

- **Shopify**: a page that loads from Shopify's CDN or sets up its `Shopify` object. It is read as a run would read it, from the first page of the collection the link names (`/collections/<name>/products/…`), or of `all`, the whole catalogue, when it names none; the linked product's offer is shown when it is on that page. Free shipping is not worked out.
- **Sitemap**, two ways: a page that gives its own price (schema.org tags or a JSON-LD Product), which needs no settings; and a page that carries its products as JSON in a script (`x = JSON.parse('…');`, the one way a store read so far does it), for which it works out the data pattern, the path to the products and which field is the model number, name, price, brand and stock. It then looks for the page in the store's sitemap (`/sitemap.xml`, then the first sitemap robots.txt names; an index is not followed) to set the sitemap path when a run would not find that sitemap by itself, and the product path pattern from what the listed paths share with the page's (a first part, `^/products/`; an ending to it, `-p/`; or, for a page at the top of the store while others lie deeper, `^/[^/]+/?$`).
- **SAP Commerce** is not recognised yet: its API's address is in no page.

Each way of reading the store also says how much there is to it (`summary`), for deciding whether it is worth collecting: a sitemap store's pages, how many are product pages and how many a run would fetch, when its sitemap last changed, and, for any kind whose reader can say how many requests a run makes, roughly how long one would take at the delay the store asks for (or the collector's own, if longer). The pages are counted by the code a run reads them with, so a run with the suggested settings fetches what was counted. When time runs out before the sitemap is found, the way of reading the page is still given, without a sitemap path, pattern or summary. When nothing reads a drive, each reader says what it looked for and what it found instead (`No price was found in the page's markup, and its JSON-LD describes no product (it describes: WebPage, Organization).`).

These are guesses from one page: check them with Test.

`collector/tests/integration/test_inspect_api.py` holds the backtests: each store already read, inspected from one of its own saved pages, must be given the settings it was set up with by hand (Seagate, ServerOrbit, goHardDrive and DiscTech from their saved pages; Shopify from a constructed page, until one is saved from ServerPartDeals). A store added later adds a case there.

### Testing a source

The collector also serves a small API beside its loop, in the same process, when `COLLECTOR_API_PORT` is set: `GET /health`, and `POST /preview`, which reads just enough of a source to show one offer and keeps nothing. A Shopify source reads one page of its first collection; a sitemap or SAP Commerce source reads its sitemap and then product pages until the first drive, five at most. A preview has its own pacer: it never waits behind a scheduled run, and waits only as long as the store's own robots.txt asks between its few requests (through a browser, as long as FlareSolverr takes). It still fetches nothing robots.txt disallows. A sitemap source given a `page_url` (*Page to test* on the form) reads that one page instead, without its sitemap. A preview reads for at most `COLLECTOR_PREVIEW_SECONDS` (default 120): once that has passed it makes no further request and fails with how far it got (`out of time after 120 seconds: 6 requests made, the last for …`), so a store that asks for a long crawl delay, or lists a great many sitemaps, cannot keep it reading after the backend has stopped waiting. The answer is `found` with the offer, `nothing` when no drive was read, or `failed` with the reason (`settings: missing collections`, `robots.txt disallows …`); each carries `notes`, sentences a sitemap source adds on what it read: how many pages the sitemap lists and how many are product pages, and for each page that gave no offer, why (`no price`, `no capacity in its name`, `16 products in its data: 16 with no price`, `could not be fetched (…)`). The API is for the backend, on the internal network; the backend reaches it at `DISKTRACKER_COLLECTOR_URL`.

With the backend running (`task dev -- disktracker`), from `stacks/apps/disktracker/collector`:

```bash
DISKTRACKER_URL=http://127.0.0.1:8000 COLLECTOR_RUN_ONCE=1 uv run --frozen python -m collector
```

It logs one JSON object per line on stdout: `ts` (UTC), `level`, `logger` (the module), `event`, and the event's fields. Each offer carries its drive's maker as `brand` (see below). It posts each offer as soon as it is read, so an interrupted run keeps what it posted. Each source's run starts with `run_started` (sitemap and SAP Commerce sources then report `sitemap_read` with how many pages they will fetch), reports `progress` every 50 offers, and ends with `run_complete`: seen, recorded, queued, ignored and failed count the offers the store listed; rechecked and recheck_failed count the offers it no longer lists. Each run then reports its counts to `POST /api/collector-runs` for the Admin page, whether it completed or failed; a report disktracker cannot take is logged as `run_report_failed` (`WARNING`) and changes nothing else. A store that fails partway logs `run_failed` with the counts so far; what was already posted stays posted. Failed pages, posts and rechecks are `WARNING`; a source that cannot be read is `run_failed` at `ERROR`; a bug is `run_crashed` at `ERROR` with its traceback in `exc_info`, and the other sources and later runs carry on. `LOG_LEVEL=DEBUG` adds every HTTP request and each posted offer. Settings: `DISKTRACKER_URL` (required), `COLLECTOR_MIN_DELAY_SECONDS` (default 2), `FLARESOLVERR_URL` (optional; needed only by sources fetched through a browser), `COLLECTOR_PROXY_URL` (optional; an HTTP proxy, such as a VPN container's, that every store is fetched through, the browser's fetches included, so stores see the proxy's address; disktracker is never asked through it, and a proxy that cannot be reached fails the fetch rather than going direct), `COLLECTOR_API_PORT` (optional; serves the preview API), `COLLECTOR_PREVIEW_SECONDS` (default 120; the longest a preview reads a store), `COLLECTOR_RUN_ONCE=1` (run what is due once and exit; otherwise it polls every `COLLECTOR_POLL_SECONDS`, default 60, until SIGTERM), `COLLECTOR_RETRY_DELAY_SECONDS` (default 0.5), `LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING` or `ERROR`; default `INFO`).

The code is split by responsibility and wired in one place, `collector/container.py` (dependency-injector). Services depend only on interfaces the collector owns (`collector/ports.py`, `Clock`): `Collector` (`collection.py`) runs one source; `Schedule` runs them all once or per interval and contains crashes; `Pacer` spaces requests by crawl delay. Adapters implement the ports: the two sources, `PoliteHttp` (robots.txt), and `DisktrackerClient` (the generated API client). Unit tests give services fakes of those owned interfaces (`tests/fakes.py`); the subprocess integration tests run the real wiring against fake HTTP servers.

The collector talks to the API through `collector/disktracker_api`, a client generated from the backend's OpenAPI spec with openapi-python-client (pinned in `scripts/generate-api-client.sh`). After changing the API, regenerate it and commit the result:

```bash
task -d stacks/apps/disktracker api-client    # from the repo root; or run scripts/generate-api-client.sh
```

A pre-commit hook (`disktracker-api-client`) regenerates it into a scratch directory and fails if the committed client is out of date. Collector checks: `uv run --frozen pytest` (unit + subprocess integration tests, 90% coverage gate), `uv run --frozen mypy`, `uv run --frozen ruff check`.

## Tests

From the repository root:

```bash
source "stacks/apps/disktracker/.local/env-$(hostname).sh"  # this container's credentials, or export your own
task test -- disktracker
task test:e2e -- disktracker
```

`task test` runs backend and frontend unit/integration tests. The separate `task test:e2e` command runs the full-application browser tests. Both use the repository's existing test runner. Unlike the development task, test commands expect the database environment to be loaded by the caller.

The frontend's `test:e2e` script invokes Python tests from the app-level `tests/e2e/` directory using the backend's locked dependencies. It is an entry point for the shared runner; browser tests stay outside both the frontend and backend directories.

For individual tiers, use `task test:unit -- disktracker` or `task test:integration -- disktracker`. Run suites sequentially to avoid competing for the local database's disk writes.

Direct lint and build commands are also available.

From `backend/`:

```bash
uv run pytest tests/unit tests/integration -q
uv run ruff check disktracker tests ../tests migrations
uv run ruff format --check disktracker tests ../tests migrations
```

From `frontend/`:

```bash
npm test
npm run build
```

From the DiskTracker directory:

```bash
backend/.venv/bin/python -m pytest -c tests/pytest.ini tests/e2e -q
```

The e2e `application_url` fixture starts FastAPI and Vite on temporary loopback ports. Its `page` fixture opens a fresh Chromium tab with UTC display time and closes it afterward. Real UI actions reach real API routes and PostgreSQL; the lost-response test deliberately discards one successful HTTP response to exercise a retry.

Follow frontend-first TDD: start with a failing test of the user-visible behavior at the appropriate level, implement only what makes it pass, then refactor. Component test files map to components; pure rules have their own unit tests. App integration tests compose the real components with a fake of our ListingsApi interface. E2E covers the main happy path and a few important failures, rather than every filter or validation rule. Do not weaken assertions to get a passing result.

## Form validation

Add offer, Record price, Edit offer, and Edit specifications forms show field errors on blur or submission, preserve entered values after failures, and focus the first invalid input on a rejected submission. Store, MPN, condition, capacity for a new MPN, and item price are required; store page URL, title, seller name, shipping & fees, and notes are optional. A price is checked now unless Change date is used. API validation remains authoritative.

Add offer (in the header, on every page) is built for speed without reading any store automatically: copy an offer's title and price from the store's page into Paste from store page and choose Fill in, and the backend (`POST /api/listing-text`) fills the MPN, capacity, condition, title and price for you to check. The form then says what it filled in and what it did not find, and moves to the first field left to fill. It takes the first line as the title and the first dollar amount that is not a Was, List, MSRP, Reg. or Save price. The store and its page's URL come first, since a later recheck opens that page. The MPN box suggests drives already recorded; the form remembers the store and condition last used (in the browser's storage), Enter saves, and Save and add another saves and starts the next offer with a fresh form.

Field rules and API-error translation have unit tests, rendered form feedback has component tests, and one browser workflow verifies that a price without an item price is refused, then saved once fixed, through the real API and database.

## Filtering and sorting

The Prices page shows one row per Drive: offers sharing an MPN are grouped, and the row shows the drive's cheapest offer in stock, in any condition, whichever way the list is ordered, with a count of the stores selling it when there is more than one. Under it the row names the other conditions the drive is sold in, each with what it costs now; choosing one opens the drive on that condition. A row shows $/TB first, then the total with what shipping adds, how long ago the offer was checked, and Stale or Out of stock where that applies; under 700px the rows become cards and a Sort by box replaces the column headings. Anywhere on a row opens the drive in a panel beside the list. The panel shows one condition at a time, since a new drive and a refurbished one are different things to buy: a Condition switch at the top lists the conditions the drive is offered in, each with what it costs now (its price, "from" the lowest of several, or Out of stock), and opens on the condition of the row chosen. Everything under it follows the switch. First an Offers table of one row per store: $/TB, total and its change since the previous price (the cheapest marked Lowest price), when it was checked, Open store page, and Record price. Record price opens a price check under the offer: No change, a new price (Enter or Save), or Out of stock, each saved in one step with the shipping last recorded; More options opens the full form for a price with its own shipping, date or notes. Below that is the price trend chart, always shown (with "No price history yet" when empty): one point per store per day (a day checked more than once shows the price it ended on), joined into a line where a store has more than one day, on a price axis that frames the prices rather than starting at zero. It is headed by the lowest in-stock total recorded for that condition with how many in-stock prices and which dates it covers (sold-out prices were not purchasable, so they never count as a low); the drive's history is loaded when it is opened; and collapsed Price history (item, shipping & fees, and total for every price across stores) and Specifications sections. The Prices page only browses and records prices; corrections live on the Admin page. What a change did is said in a message at the foot of the window, which stays in view over the panel.

The first row filters by name/MPN/store, media type, capacity and maximum total. Under it, Condition is a row of buttons, one for each condition there are offers in, with how many drives are sold in it: none pressed accepts any condition, and pressing some prices and orders every drive by its offers in those alone, so a drive whose new price is the bargain is ranked by it once New is pressed. The line above the table says which conditions the prices come from. More filters holds brand, store, the other specifications, In stock only and Checked in the last 7 days, and counts how many of those are in force. Brand and Capacity are searchable dropdowns built from the drives loaded, each option showing how many drives have it; drives no source has named a brand for are listed under Unknown. Every filter applies as it is chosen; a typed maximum total applies once typing pauses (or at once on Enter), so a half-typed amount never filters the list. No filters are selected initially. Each other filter in force is a chip that removes it; Clear filters removes them all, conditions included, and retains the sort order. Filters and sorting survive reloads through URL query parameters. Saving an offer preserves filters and provides a Show drive action if the saved entry is hidden.

The default sort is $/TB ascending. Total, capacity, and observation time can also be sorted in either direction. Lowest-total and lowest-$/TB labels consider only matching listings with a recent observation; ties keep the same label. Older prices remain visible with Needs recheck.

The recent-observation window defaults to seven days. Set `VITE_DISKTRACKER_RECENT_DAYS` when starting Vite or building the frontend to change it; a positive number is required. This is an age threshold, not a guarantee that an offer remains available. Age is recalculated when the view renders; an idle page does not poll for updates.

Filtering currently runs in the frontend over the listings returned by the API. Interface, recording-type, and intended-use filters use the entered specifications described below.

## Shared drives and specifications

An offer is identified by MPN + store + seller name + condition. The store is where it is sold: one of the sources on the Admin page, which are every store offers are recorded under, collected or entered by hand (seeded with ServerPartDeals, goHardDrive, Western Digital and Other), its value the source's key; Other is for a one-off store. Seller name is asked only for Other, where it is required and names the store ("Micro Center"). Offers display as the store, or the store's name for Other. Condition is one of New, Manufacturer recertified, Refurbished, or Used. Recording a price with Add offer finds that offer or creates it, then appends the price; recording from an offer row keeps that offer's identity. Every offer for an MPN links to one shared Drive record, created with Unknown specifications the first time the MPN is seen.

Capacity belongs to the drive. The first price for a new MPN picks a capacity from standard sizes (1–32 TB) or enters another size under Other; later prices for that MPN reuse the recorded capacity, and a conflicting capacity is rejected. Change a drive's capacity in Edit specifications, which recalculates $/TB for every offer of that MPN.

Specifications (interface, recording type, intended use) belong to the Drive, not the listing, so they're entered once and shared by every listing for that MPN. Use Edit specifications from the drive's details on the Admin page to change them and the drive's capacity. Interface and recording type are single choices that start as Unknown; intended use is any combination of NAS, Surveillance, Enterprise, Desktop, and Archive, and shows as Unknown when none is chosen. The Specifications section shows each value, and the filters under More filters match these values (Unknown matches drives where it was never entered).

## Admin

`/admin` (Admin in the header, with a count of what is waiting) is where the data is managed, on three tabs, each with its own address:

**To do** (`/admin`): what waits on a person.

- **Collectors:** what the collector is doing now: the store it is running, for how long and how many offers it has read; the stores waiting, in the order they will run; and a warning when the collector has not been heard from for five minutes (it says something at least every minute, so it may be down or restarting). Under that, how many collectors finished their last run, and each one whose last run failed. This and the Stores tab are asked for again every 15 seconds while the page is open.

- **Recheck by hand:** offers entered by hand and not checked in the recent window (7 days by default), oldest first; collectors keep their own offers current. Open the store page, then record what it shows in one step: No change (moves only when it was last checked), a new price (Enter or Save), or Out of stock. Nothing else can be answered for an offer while one answer is being saved.
- **Needs matching:** offers a collector read but could not match to a drive, to resolve or ignore. Ignore asks first. If they cannot be loaded, it says so with Try again, rather than that there are none.

**Stores** (`/admin/stores`): how the data is collected.
- **Stores:** every store offers are recorded under; a source is the store. Each row shows how it is collected, its schedule and where it stands (running now, next to run, its place in line, or when it is next due), how its last collector run went (when it finished, whether it completed or failed, and what it saw, recorded, queued, failed and rechecked), how many offers it has and the median age of their last checks, and the permission it is collected under. Adding one needs only a name and a type: Shopify, Sitemap + product page or SAP Commerce, which the collector reads from its store URL, or *Entered by hand*, a store whose prices are only ever entered (its URL is optional, and it has no schedule, permission, switch or Run now; Other is one). Its key, fixed from its name, is what its offers, prices and runs are recorded under, and it is offered in the Store filter and Add offer straight away. A collected source can read several collections at once. Under *Advanced*: a five-field cron schedule in UTC (validated), an on/off switch, how its pages are fetched (directly, or through a browser, FlareSolverr), a permission (permission granted, terms allow, open API, or unconfirmed; shown, not enforced), and notes. Each type has its own settings (see Collector); the backend fills in defaults and refuses settings that do not fit the type. The list shows when each is next due: the first time its schedule fires after its last run started, *Due now* once that has passed (or straight away for a source that has never run), and — while switched off. *Run now* makes a source due at once, switched on or not, until a run of it starts, and puts it ahead of the stores only scheduled: it runs as soon as the store being collected is done. A store that is running shows how far it has got in place of its last run, and *Stop* in place of Run now: once confirmed, the collector ends that run within seconds (at its next report, so after the page it is reading), keeping what it has recorded, and the run is shown as Stopped. ServerPartDeals, goHardDrive and Western Digital are seeded as sources (migration 0024), which also makes Other, and any other store offers were recorded under, a source entered by hand under the same key, so no offer moves. A source is always given with the settings its kind has now: defaults for any added since it was saved, without any dropped since. *Test*, in the form, tries a source before it is saved (or as edited): the backend checks it as a save would and asks the collector to read one offer, then shows that offer and what disktracker would do with it (record it; hold it under Needs matching, and why; or ignore it because it is sold out). Nothing is saved, and it needs the collector running. *Delete store*, in a store's edit form, removes a source nothing is recorded under, with its collector runs; one with offers or queued offers can only be switched off, and Other is always kept.
- **Condition rules:** which text names which condition. Each rule is a case-insensitive regular expression (`\b` marks a word boundary) and a condition; the collector and Paste from store page read them in order against a listing's title and the store's own condition field (a Shopify `condition:` tag), and the first rule that matches anywhere wins, so a title saying *Renewed* outranks a *New* tag when the *renewed* rule comes first. Seeded with the phrases the readers knew (migration 0024); edited, reordered, added or removed here and saved together. A drive that a changed rule now reads under another condition is recorded on a listing for that condition; its old listing is marked out of stock by the next run, not rechecked.

**Drives** (`/admin/drives`): every drive, searchable by name, MPN or store, and narrowed with one choice to those with no known specification or with an in-stock offer not checked in the recent window (choose it again to clear). Opening one shows its details with every correction: Edit specifications (including the brand and other MPNs), and Edit offer, Delete offer and Delete price.

The counts are computed in the browser from the offers and queue the app already loads; only collector runs come from their own endpoint. A tab not being shown keeps what was typed in it.

## Fixing mistakes

These are all on the Admin page's Drives tab, in a drive's details. Prices are append-only: recording a price never rewrites an earlier one. To fix a mistyped price, expand Price history, choose Delete price, and record the right one. Deleting an offer's only price removes the offer. Edit offer changes an offer's title or URL in place; its MPN, store, seller name, and condition identify it and cannot be edited, so delete the offer and record the price again under the right identity. Delete offer removes an offer and all of its prices. Edits and deletes are not kept as history.

Restart the development task after pulling these changes: it applies pending migrations before starting the backend. Migration `0007` normalizes conditions (seller refurbished and unknown become Refurbished; open box becomes Used) and merges offers that become duplicates, keeping every price. Migration `0008` removes correction history, archives, and edit revisions. Migration `0009` splits free-text sellers into a store and seller name ("eBay - Beach Audio" becomes eBay · Beach Audio; unrecognized names become Other), merges spelling variants, and gives offers without an MPN a placeholder `UNCONFIRMED-…` MPN. Migration `0010` moves capacity onto drives, taking the capacity most of each drive's offers recorded. Migration `0011` removes prices without an item price (and offers left with none), folds fees into shipping, treats unknown shipping as $0, and drops availability. Migration `0012` keeps only the plain value of each specification, dropping verification status, sources, Other descriptions, and SMR management. Migrations `0013`–`0016` add last-checked times, unknown shipping, stock status, and MPN aliases, and normalize existing MPNs (drives whose MPNs would collide once normalized are left separate; join them with an alias). Migration `0024` makes every store a source (the three collected stores, Other, and any other store offers were recorded under), names an offer's store by its source's key, and adds the condition rules. Migration `0023` adds each drive's brand, unknown until the next collector run names it. Migration `0021` turns offers from stores disktracker does not collect from (Newegg, Amazon, eBay, B&H, Best Buy) into Other, named after the store and any marketplace seller ("eBay · Beach Audio").

## API

- `GET /api/listings`: every offer with its latest price (`latest`) but not its history, so the list stays small as prices accrue. `?store=` narrows it to one store.
- `GET /api/price-history?listing={id}&listing={id}…`: the named offers with their full history (`observations`, oldest first). The app asks for this when a drive is opened. Unknown ids are skipped.
- `GET /api/listings/{id}`: one offer and its history.
- `POST /api/prices`: record a price. The body carries the offer identity (`mpn`, `store`, optional `seller`, `condition`), its details (`title`, `url`), the drive's `capacity_tb` (required only for an MPN not seen before), and the price (`item_price_cents`; `shipping_cents` for shipping & fees — omitted means 0, `null` means unknown; `in_stock`, default true; `observed_at`, default now; `notes`). `title` and `url` are used only when the offer is created (a new offer without a title is named by its MPN); later prices never overwrite them. A price identical to the offer's latest (same item price, shipping, and stock status) is not stored again; it only moves the offer's `last_checked_at`. `item_price_cents` may be omitted only with `in_stock: false`, which records the offer as sold out at its last known price; a new offer always needs a price. MPNs are stored uppercase without whitespace, and an alias MPN routes to its drive. Finds or creates the offer, updates its details, and appends the price. Prices under a `store` that is no source's key are refused (422 on `store`).
- `PATCH /api/listings/{id}`: change an offer's `title` or `url` in place.
- `DELETE /api/listings/{id}`: delete an offer and its prices.
- `DELETE /api/listings/{id}/observations/{observation_id}`: delete one price. Returns the remaining offer, or 204 when that was the offer's last price and the offer was removed.
- `POST /api/drives/{id}/aliases`: declare another MPN (`{"mpn": ...}`) for a drive. Later prices under it join the drive; a drive already recorded under it is merged in, combining the prices of offers that match. 409 if the MPN is the drive's own or another drive's alias.
- `GET /api/sources`, `POST /api/sources`, `PUT /api/sources/{id}`: the configured sources, by name (`kind` is `shopify`, `sitemap`, `sap_commerce` or `manual`, entered by hand, which needs no `base_url` and is never due; `schedule` defaults to every 8 hours, `enabled` to true, `basis` to unconfirmed), each with `transport` (`direct`, the default, or `browser`) and `next_run_at`, when it is next due (in the past while it waits for the collector; null while switched off and not asked to run). `GET /api/sources/due`: the sources due now, most overdue first. `POST /api/sources/{id}/run` (202): makes a source due now until a run of it starts; 404 for an unknown source. A missing or non-http(s) URL for a collected kind, a schedule that is not five-field cron, or an unknown kind is refused on that field; a duplicate name is 409.
- A scraped offer (`POST /api/scraped`) names only its `source`, which is the store it is recorded under; a queued offer does the same.
- `GET /api/condition-rules`, `PUT /api/condition-rules`: the condition rules in order (`pattern`, `condition`); a PUT replaces them all. A pattern that is not a regular expression, or an unknown condition, is refused on that rule's field (`["body", index, field]`).
- `POST /api/collector-runs`: a collector reports one run (`source`, `started_at`, `finished_at`, `completed`, `stopped` when it ended because it was asked to, and the `seen`, `recorded`, `queued`, `ignored`, `failed`, `rechecked` and `recheck_failed` counts). `GET /api/collector-runs/latest` returns each source's most recent run, by source.
- `PUT /api/collector-activity`: a collector says how far a run in progress has got (`source`, `started_at`, and the `seen`, `recorded`, `queued`, `ignored` and `failed` counts so far); the answer's `stop` says whether that run was asked to stop. `GET /api/collector-status` returns when a collector was last heard from (`seen_at`, null if never), the runs in progress (`running`, each with `updated_at`), and the keys of the sources `waiting`, in the order they will run. `POST /api/sources/{id}/stop` (202) asks the source's run in progress to stop; 404 for an unknown source. `GET /api/sources/due` is asked only by a collector, between runs: it lists those asked to run first, and clears the runs in progress.
- `PUT /api/drives/{id}/specifications`: replace a Drive's `capacity_tb` and `specifications`; every offer linked to that Drive reflects the change immediately. `brand`, when given, sets the drive's maker by hand (blank makes it unknown again); a source only names a drive that has no brand, so a corrected one is left alone.
- `POST /api/source-previews`: try a source without saving it. The body is a source as `POST /api/sources` takes it; the answer has `status` (`found`, `nothing`, `failed`), `reason`, the `offer` read, and a `verdict` (`outcome`: `recorded`, `review` or `ignored`, with its `reason`). 422 for a source that could not be saved; 503 when there is no collector to ask.
- `DELETE /api/sources/{id}`: 204; 409 when offers or queued offers are recorded under it, or it is Other; 404 for an unknown source.

Offer responses include `store`, `seller`, `capacity_tb` (from the drive), `last_checked_at`, `store_name`, `drive` (`{id, mpn, aliases, brand, capacity_tb, specifications}`; `brand` is null until a collector names it), and `latest`; every response except `GET /api/listings` also carries `observations`. Each observation has `in_stock` and `shipping_known`; unknown shipping counts as $0 in `total_cents` and is shown as "Shipping not included". Sold-out offers are never marked lowest, and "checked recently" uses `last_checked_at`. The `specifications` object is `{interface, recording_type, intended_use}`: `interface` is one of `sata`, `sas`, `nvme_pcie`, `usb`, `unknown`; `recording_type` one of `cmr`, `smr`, `unknown`; `intended_use` a list of `nas`, `surveillance`, `enterprise`, `desktop`, `archive`. Other values are rejected.

`POST /api/prices` requires a UUID `Idempotency-Key`. Reuse it when retrying the same request; a changed payload with the same key returns 409. Observation times must include a timezone. Currency is USD; amounts use integer cents, and capacity is a decimal TB string. Full request schemas are available at the local API's `/docs` endpoint.
