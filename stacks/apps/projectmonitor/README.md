# Project Monitor

Project Monitor is a CI build dashboard created by **Pivotal Labs and the original
Project Monitor contributors**. This homelab fork imports the application from
[`vmware-archive/projectmonitor`](https://github.com/vmware-archive/projectmonitor/tree/2b85d1701007d832cbc4b49aa3c94cbacb076884)
at commit `2b85d1701007d832cbc4b49aa3c94cbacb076884`. The forked application and its
original tests live in [`app/`](app/); there is no nested Git repository or
submodule to initialize. The original dependency lock is recorded in
[`app/Gemfile.upstream.lock`](app/Gemfile.upstream.lock).

The runtime is Ruby **3.4.11**, Rails **8.1.4**, Puma, and MariaDB **10.11.14**.
Node **22.23.4** comes from the official Node image for asset compilation and
browser tests; npm rejects local runtimes older than Node 22.
The image uses the official Ruby Debian Bookworm base and runs as UID/GID 1000.
One application image serves four roles: web, delayed-job worker, EventMachine
poller, and Clockwork housekeeping. MariaDB has its own service and OCFS2 volume.

## Repository layout

This service follows the monorepo's `app/` convention. Here, `app/` contains the
**vendored fork's repository root**, including its dependencies, tests, licenses,
and Rails directory structure. The nested `app/app/` is Rails' own application
directory.

```text
projectmonitor/
├── README.md                 # Homelab operation and fork provenance
├── docker-compose.yml       # Swarm service definition
├── pre-flight.yml           # Homelab provisioning
└── app/                     # Vendored Project Monitor repository root
    ├── README.md            # Application guidance and upstream credits
    ├── LICENSE, MIT.LICENSE, NOTICE
    ├── Gemfile, Gemfile.lock
    ├── Gemfile.upstream.lock # Original dependency lock for provenance
    ├── package.json         # Browser test dependencies and homelab test commands
    ├── package-lock.json
    ├── compose.test.yml     # Disposable container test environment
    ├── script/              # Test runners and coverage maintenance
    ├── app/                 # Rails models, views, controllers, and assets
    ├── config/, db/, lib/
    ├── spec/                # Application tests
    └── Dockerfile, docker/  # Container support added for this fork
```

The import is a source snapshot at the pinned upstream commit, followed by the
homelab changes. Upstream's full Git history remains in the linked repository;
it was not imported into this monorepo. The fork is maintained here, with no
separate GitHub fork, submodule, or automatic upstream synchronization.

## Upstream credit and licenses

Credit for the original application belongs to Pivotal Labs and the
[upstream contributors](https://github.com/vmware-archive/projectmonitor/graphs/contributors).
The homelab work updates dependencies, adds container and Swarm integration, and
adapts compatibility and test tooling; it does not claim original authorship.

The upstream files are preserved verbatim:

- [`app/LICENSE`](app/LICENSE): the BSD 2-clause license text.
- [`app/MIT.LICENSE`](app/MIT.LICENSE): the MIT license with
  **Copyright (c) 2010 Pivotal Labs**.
- [`app/NOTICE`](app/NOTICE): **Copyright 2022 VMware, Inc.** and the upstream
  licensing notice.

The [application README](app/README.md) also retains upstream's 2018 Pivotal Labs
credit. Keep these files and third-party notices with the imported source and
distributions. The Docker build copies the application README and all three files
into `/app` in the production image.

## Build, test, publish, deploy

From the homelab repository root:

```bash
task test -- projectmonitor
task build -- projectmonitor
task publish -- projectmonitor
task deploy:plan -- projectmonitor
task deploy -- projectmonitor
```

The default image tag is `latest`, matching `task build` and `task publish`.
`REGISTRY`, `REGISTRY_NAMESPACE`, and `IMAGE_TAG` use the standard homelab
conventions. Set `IMAGE_TAG` to a published release tag when pinning a deployment.
The test manifest is separate from the Swarm manifest and provisions only a
disposable database; it never uses the homelab database volume.

Set these four independent values in the root `.env` before deployment:

| Variable | Generate with |
| --- | --- |
| `PROJECTMONITOR_DATABASE_PASSWORD` | `openssl rand -hex 32` |
| `PROJECTMONITOR_DATABASE_ROOT_PASSWORD` | `openssl rand -hex 32` |
| `PROJECTMONITOR_SECRET_KEY_BASE` | `openssl rand -hex 64` |
| `PROJECTMONITOR_PASSWORD_PEPPER` | `openssl rand -hex 32` |

Pre-flight provisions them as external Swarm secrets and creates
`/mnt/iscsi/app-data/projectmonitor/database`, owned by MariaDB's UID/GID 999.
A node must have `node.labels.database == true` and mount that shared storage.
Keep the session secret and password pepper stable across redeployments.

The dashboard is at `https://projectmonitor.${BASE_DOMAIN}`, behind Traefik TLS
and Authentik forward authentication. Authentik grants access to the dashboard;
Project Monitor's own account controls project administration. The stack declares
both required dependencies in `x-homelab.requires`.

## First administrator

Set `PROJECT_MONITOR_LOGIN`, `PROJECT_MONITOR_EMAIL`, and
`PROJECT_MONITOR_PASSWORD` in `.env`. These are used only for a one-off bootstrap;
they are not passed to the running services. Locate the node running the web task
with `docker service ps projectmonitor_projectmonitor`.

On that node, with those three variables exported from your configuration:

```bash
docker exec \
  -e PROJECT_MONITOR_LOGIN -e PROJECT_MONITOR_EMAIL -e PROJECT_MONITOR_PASSWORD \
  "$(docker ps -q --filter label=com.docker.swarm.service.name=projectmonitor_projectmonitor)" \
  /app/docker/entrypoint.sh bundle exec rake db:seed
```

The entrypoint loads the Swarm secrets for this command. Upstream's seed task
creates or updates the specified account, so rerunning it resets that account's
password. Regular service restarts do not run the seed task.

## Storage and startup

The web task waits for MariaDB, runs `db:prepare`, and then starts Puma. The other
roles wait for the schema before starting their foreground processes. A single
web replica and `stop-first` updates prevent two web tasks from migrating at once.
Readiness checks verify the web version endpoint and MariaDB initialization.
The 90-second stop grace period allows the worker to finish its one-minute jobs.

Fresh databases load the upstream schema snapshot using Rails' 4.2 compatibility
semantics. Historical migrations are retained verbatim for provenance; some
contain class-body SQL from early Rails versions and must not be replayed as a
fresh-install procedure. `db:prepare` records those versions from the snapshot.
An existing installation should be brought to the upstream schema version
`20161014211931` and backed up before importing its database.
An existing production database upgrade has not been tested.

All routes currently require Authentik. If using CI webhooks, configure a
separately reviewed machine-authentication policy for the webhook route before
pointing external senders at it. Polling requires no public webhook access.

## Compatibility scope

| Component | Upstream | Homelab fork |
| --- | --- | --- |
| Ruby | 2.3.1 | 3.4.11, official Debian Bookworm image |
| Rails | 4.2.7 | 8.1.4 |
| Web server | Unicorn | Puma |
| Database | Bundled MySQL installation | Separate MariaDB 10.11.14 service |
| Browser tests | Qt WebKit / PhantomJS | Chromium, Selenium, and Playwright |
| Deployment | Standalone scripts | Swarm compose, declarative pre-flight, standard homelab tasks |

The fork preserves the application behavior. Compatibility changes cover removed
Rails callbacks, relation and serialization APIs, URI/File APIs, dynamic method
delegation, explicit uniqueness semantics, and the replacement of `choices` with
a tested settings loader. Session signing now reads the deployment secret.

The original Backbone/CoffeeScript/Eco UI, vendored browser libraries, and Sass
styles remain. Bourbon 4.3.4's stylesheets are vendored with their license because
its Ruby package pins an obsolete Thor dependency; this preserves the existing
mixins and rendered design. SassC and legacy asset adapters remain compatibility
dependencies, so this is not a claim that every frontend component is maintained.
CI adapter behavior is preserved; live provider compatibility needs verification
against the projects you configure.

Airbrake and New Relic reporting are inactive without explicit account settings.
The system certificate bundle replaces the archived CA bundle in the deployment.

## Retired tooling

The fork removes Vagrant/Chef provisioning, the old host bootstrap script,
upstream Travis/Concourse pipelines, Guard/autotest, obsolete Rails launchers,
and setup tasks that replaced `config/database.yml`. Use the monorepo tasks above
and the environment-driven database configuration. The default `bundle exec rake`
now runs the full test entrypoint instead of removed Jasmine/JSHint tasks.

Cloud Foundry helpers and their tests, legacy cron settings, bundled certificates,
and UI help documents remain pending separate compatibility review. The original
upstream commit provides the history of the removed tooling.

## Tests and coverage

`task test -- projectmonitor` is discovered by the existing CI tooling through the
application's `app/package.json`; no root Taskfile changes are needed. It builds the
Dockerfile's test stage, starts disposable MariaDB, and runs:

1. All RSpec examples, including upstream browser and recorded API tests
   and regression tests for configuration and container startup.
2. The changed-line coverage gate for application/library compatibility edits and
   the new settings loader and database readiness helper.
3. All 123 JavaScript specs, using Jasmine 5 and Chromium via Playwright.

Qt WebKit and PhantomJS are replaced by Chromium. Existing assertions are
retained; test calls use modern framework APIs. VCR tests replay their checked-in
responses without attempting to refresh expired recordings. Clock and browser
login state are isolated between tests. The RubyGems status test explicitly
establishes the original four-failure threshold instead of depending on a previous
example's counter.

`app/coverage/` contains the Ruby report. The coverage manifest records changed
lines against the pinned upstream and hashes the files; stale manifests or
unexecuted changed lines fail the test command. To regenerate after a compatibility
edit, use a clean checkout of the exact upstream commit:

```bash
python3 stacks/apps/projectmonitor/app/script/update-coverage-baseline.py /path/to/upstream
task test -- projectmonitor
```

For development without Docker, provision Ruby 3.4.11, MariaDB, Node 22+, and Chromium;
create a disposable `projectmonitor_test` database and run `bundle install` inside
`app/`. Then run the same Taskfile entry point with explicit test credentials:

```bash
PROJECTMONITOR_TEST_LOCAL=1 \
DATABASE_HOST=127.0.0.1 DATABASE_USER=projectmonitor DATABASE_PASSWORD=... \
CHROME_BIN=/path/to/chromium task test -- projectmonitor
```

The unit and integration task aliases run the complete suite because upstream's
fixtures and Rails examples share the same database harness.
