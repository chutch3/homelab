# Contributing

Project Monitor is maintained under `stacks/apps/projectmonitor/` in the homelab
monorepo. See the [service README](../README.md) for runtime requirements and local
setup.

## Architecture

The Backbone/CoffeeScript frontend polls the Rails backend for updates. The
backend polls CI providers or receives webhooks, and delayed-job workers process
queued work. Separate EventMachine and Clockwork processes handle polling and
housekeeping.

The application renders project setup help from `docs/adding_a_project/` using
Kramdown. Keep those documents when changing developer documentation.

## Running tests

From the homelab repository root:

```bash
task test -- projectmonitor
```

This provisions a disposable database and runs the Ruby/browser specs, the
compatibility coverage gate, and the JavaScript specs. Follow the service README
for `PROJECTMONITOR_TEST_LOCAL=1` when using a locally installed runtime.

Inside an already configured application test environment, the equivalent full
suite is:

```bash
RAILS_ENV=test bundle exec rake
```

The test entrypoint loads the schema into `projectmonitor_test`; use a disposable
database with credentials dedicated to testing. It uses Chromium for both Selenium
and Playwright. Install the dependencies with `bundle install` and `npm ci` when
working outside the test image.

For a focused Ruby example, use `bundle exec rspec path/to/spec.rb`. Run
`npm run test:javascript` for the JavaScript suite. Run the full suite before
submitting changes so the changed-line coverage gate can evaluate every affected
application file.

## Compatibility changes

Preserve application behavior and add regression coverage for compatibility
edits. Do not remove assertions to make dependency upgrades pass. The coverage
manifest is generated against the pinned upstream commit; the service README
explains how to regenerate it after an application edit.

Keep the existing frontend assets, provider fixtures, licenses, and historical
migrations unless a change explicitly addresses their behavior or retirement.
Deployment uses the service's Dockerfile, Compose manifests, and pre-flight file.
