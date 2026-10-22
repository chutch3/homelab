# Project Monitor modernization

Project Monitor is vendored into this monorepo at
`stacks/apps/projectmonitor/app`, from upstream
commit `2b85d1701007d832cbc4b49aa3c94cbacb076884`. There is no nested repository or
submodule. The service README at `stacks/apps/projectmonitor/README.md` documents
configuration, administrator bootstrap, tests, and deployment.

## Implemented

| Component | Upstream | Fork |
| --- | --- | --- |
| Ruby | 2.3.1 | 3.4.11, official Debian Bookworm image |
| Rails | 4.2.7 | 8.1.4 |
| Web server | Unicorn | Puma |
| Database | Bundled MySQL installation | Separate MariaDB 10.11.14 service |
| Browser tests | Qt WebKit / PhantomJS | Chromium, Selenium, and Playwright |
| Deployment | Standalone scripts | Swarm compose, declarative pre-flight, standard homelab tasks |

The stack includes web, worker, poller, housekeeping, and database services.
Traefik provides TLS and Authentik protects the dashboard. Database credentials,
session signing material, and the password pepper use Swarm secrets. The existing
Taskfile and CI discovery find the service without root Taskfile changes.

Application changes are limited to framework/runtime compatibility. The original
Ruby and JavaScript examples remain, with test-harness updates and additional
configuration/startup regression tests. A changed-line coverage gate checks every
modified executable application/library line against the pinned upstream, plus
the new settings loader and database readiness helper. It rejects stale file
hashes and unexecuted changed lines.

## Validation and remaining limits

Validation uses the same Ruby version and MariaDB release locally: 854 Ruby
examples and all 123 JavaScript specs pass, and all 70 changed executable lines
covered by the compatibility gate are exercised. Checks include production asset
compilation, login, project administration, background startup, job processing,
and worker shutdown. Compose, Docker build target
discovery, pre-flight schemas, dependency declarations, shell scripts, and the
Dockerfile are checked separately.

The execution environment has no usable Docker daemon. The production/test images
have not been built or run here, and no image has been published or Swarm stack
deployed. Run `task test -- projectmonitor` and `task build -- projectmonitor` on a
Docker host before publishing and deploying.

The original Backbone/CoffeeScript/Eco frontend and legacy asset adapters remain
to preserve behavior. This work does not make every vendored browser dependency
current. Recorded CI-adapter tests do not establish compatibility with today's
live provider APIs.

Fresh installations load the original schema using Rails 4.2 compatibility
semantics. Historical migrations remain byte-identical to upstream and are not
the fresh-install path; some contain SQL executed while loading migration classes.
Restoring an existing installation requires a backup and a database already at
upstream schema version `20161014211931`. No existing production database upgrade
has been tested.
