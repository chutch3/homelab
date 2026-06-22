# Monorepo build & release plan

Status: draft / for review
Scope: how buildable apps in this repo get built, tested, versioned, and released.

## Why

The repo holds two different kinds of thing under one toolchain:

- **Service definitions** — ~40 `stacks/apps/*/docker-compose.yml` that wire up an upstream image. No build step.
- **Buildable products** — a handful of dirs with real source and a Dockerfile: `fiber`, `warden`, `takeout-manager` (manager + worker + a JS frontend), `kolibri`, `monitoring/custom-exporter` (+ `iperf3-server`), and the shared `images/devbox`.

Today the second group is unmanaged:

- **No CI builds or pushes any custom image.** Every one reaches ghcr only when someone runs `task <app>:publish` from a laptop — no provenance, no reproducibility, and whatever arch the laptop happens to be.
- **Only `fiber` runs tests in CI.** `warden`, `takeout-manager`, and `custom-exporter` ship test suites that CI never runs.
- **The one always-on workflow (`ci-cd.yml`) is repo-wide and coarse** — it lints the whole tree on every push but builds/tests nothing per app.
- **Deploys pull `:latest`** (except devbox, which already pins by digest), so swarm nodes can run different builds of the same tag.
- **Per-app `Taskfile.yml`s are near-identical boilerplate** duplicated 5×, with three different placeholder namespaces and inconsistent env prefixes (`kolibri` and `devbox` use bare `REGISTRY_*`, which collide with the global namespace).
- **One whole-repo version.** `python-semantic-release` versions everything together on a weekly cron, decoupled from any image tag.

## Goals

- Build and test only the apps a change actually touches.
- Every buildable app tested in CI, every image built by CI (not by hand).
- Immutable, reproducible image references; deploys pin a real version, not `:latest`.
- Apps release on their own cadence; the homelab release records which app versions ship.
- Keep the moving parts small and unit-testable. No heavyweight build system.

## Non-goals

- No Bazel / Nx / Pants / moon. The apps are independent (no shared internal libraries), so a dependency-graph build system buys nothing here. The one real cross-image edge (devbox) is handled explicitly.
- No physical relocation of apps out of `stacks/apps/` in this plan (see Out of scope).
- No change to the Docker Swarm / Ansible deploy mechanism itself.
- **No merge queue.** A single maintainer with low PR volume doesn't need automated rebase/serialized merges; trunk + the required gate (§3) is enough. Revisit if concurrent PRs start colliding. (A queue would re-run the gate check, which is fine.)
- **No feature flags / release branches.** Continuous merge to `main` plus per-app tags is the release strategy; there's no user-facing rollout to gate. Listed only because the reference best-practices call it out — it doesn't apply to infra here.

## Design

### 1. The unit is a compose service that declares `build:`

No new per-app file. A buildable **unit is a compose service with a native `build:` section** — Compose's `build:` key (`context`, `dockerfile`, `platforms`) names where the image comes from, right next to the `image:` it produces. Swarm ignores `build:` at `docker stack deploy` (verified against the swarm schema — it validates and is skipped, since swarm pulls rather than builds), and `docker buildx bake` consumes it directly. The only thing compose can't express — which paths trigger a rebuild — goes under an **`x-homelab.watch`** extension on the same service (`x-*` is spec-defined metadata Docker carries through and ignores — verified). `watch` globs are repo-root-relative (so they match the paths `git diff` reports); omit `watch` and it defaults to the service's own stack dir. **Nothing about testing lives in compose** — tests are discovered structurally (see Testing).

A service per image means `takeout-manager`'s `manager`/`worker` are two units that rebuild independently, no duplicated image name.

```yaml
# stacks/apps/warden/docker-compose.yml — a normal buildable service
services:
  warden:
    image: ${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE}/warden:1.4.0   # released tag, literal (no env var)
    build:                       # native compose; ignored by swarm, used by bake/CI
      context: .
      dockerfile: app/Dockerfile
    # no x-homelab needed — watch defaults to stacks/apps/warden/**
```

**Shared base images are not their own unit.** `images/devbox/` is just a shared `Dockerfile`. The apps that use it — `claudecodeui`, `code-server` — each point their service's `build.dockerfile` at it and add an `x-homelab.watch` listing the shared path (this is the one case the default doesn't cover):

```yaml
# stacks/apps/code-server/docker-compose.yml
services:
  code-server:
    image: ${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE}/homelab-devbox:1.2.0
    build:
      context: ../../../images/devbox     # compose-relative (compose's rule)
      dockerfile: Dockerfile
    x-homelab:
      watch: ["stacks/apps/code-server/**", "images/devbox/**"]   # app OR shared Dockerfile
# claudecodeui/docker-compose.yml carries the same build: + watch (the shared path duplicated)
```

A change to `images/devbox/Dockerfile` matches **both** apps' `watch` globs, so both are flagged. That is the design point: change detection must fan one file out to every unit that depends on it (§2) — there is no standalone unit, bake file, or derived edge for the base image. (Both reference the same `homelab-devbox` image, so the build dedups by image ref — §2 — building once while both apps redeploy.)

**`watch` ⊇ `build.context` invariant.** `watch` must cover everything the build reads, or you ship a stale image silently: `warden`'s context is `.` (the whole stack dir), so a change to a stack-root file the Dockerfile `COPY`s would change the image — but a narrow `watch: ["stacks/apps/warden/app/**"]` would miss it. So `watch` defaults to the whole stack dir; narrow it only when you're sure. The schema check (§ Changes) resolves `build.context` (compose-relative) to repo-relative and verifies `watch` covers it.

### 2. Change detection — a pure function

The only non-trivial logic is "given the changed files, which units are affected." Keep it pure and testable; keep git and CI out of it.

```python
# tools/ci/ci/affected.py (sketch)
def discover_units(repo_root) -> list[Unit]:
    """Every compose service with a `build:` block under stacks/apps/**.
       Each Unit carries its image ref, build context, watch globs, and test."""

def affected_units(changed_files, units) -> list[str]:
    """Many-to-many: return EVERY unit with a watch glob matching ANY changed
       file. One shared file (e.g. images/devbox/Dockerfile) can therefore
       flag several units at once — that fan-out is the contract, not an edge case."""
```

`discover_units` parses the compose files; `affected_units` is a pure function over the parsed units, so tests feed unit lists and changed-path lists with no YAML or git. Two properties to test explicitly:

- **Fan-out.** A single changed path that several units watch returns all of them (the shared-`Dockerfile` case, and any shared script multiple Dockerfiles `COPY`).
- **Build dedup.** When two affected units resolve to the *same* image ref (the two devbox consumers → `homelab-devbox`), the build step builds and pushes that image once; both units still proceed to test/redeploy. Dedup is keyed on the image ref, not the unit.

- Side-effecting part (CI only, untested): `git diff --name-only <base>...HEAD` → pipe into the script → emit a JSON array → feed `strategy.matrix`.
- Pure part (unit-tested, no git/docker): changed paths in → affected image names out, including the base→consumer fan-out.

Two implementation details that are easy to get wrong and belong in the script, not glossed:

- **Diff base.** Checkout must use `fetch-depth: 0` or there is no base to diff against. The base itself differs by event: `github.event.pull_request.base.sha` on PRs vs `github.event.before` on push to `main` — and `before` is all-zeros on the first push / a force-push, so fall back to building everything when it can't be resolved.
- **Build-tooling changes rebuild everything.** A change to `tools/ci/ci/affected.py`, `.github/workflows/build.yml`, or a shared base fragment affects every image but matches no unit's `watch`. Treat those paths as a wildcard that marks all units affected, so build-logic changes can't ship to nothing.

### 3. CI pipeline

One workflow replaces the current per-app sprawl. Two jobs: `detect` emits the affected matrix; `build-test` runs once per affected unit.

| Trigger | Action |
| --- | --- |
| PR touching a unit | run its tests (§6), then `docker buildx bake <service>` — **no push** (gate only) |
| Merge to `main` | `test` + bake + push `<image>:<sha>` and `:main` — a deployable image per commit, not a release |
| Tag `<app>-vX.Y.Z` | **promote** the already-tested `:<sha>` image to `:X.Y.Z` (see §4) |

The matrix builds with `docker buildx bake -f <the service's docker-compose.yml> <service>` — bake reads `context`/`dockerfile`/`platforms` straight from compose. No separate build script to keep in sync; CI sets tags and cache flags as `--set` overrides, and dedups by image ref (§2) so a shared image builds once.

`detect` short-circuits (`if: needs.detect.outputs.units != '[]'`) so unrelated changes do no build work. The repo-wide lint in `ci-cd.yml` stays global — it is cheap and catches cross-cutting YAML/shell issues.

**Required-check gate (do not skip this).** A path-filtered matrix and branch protection are a known deadlock: if `build-test` is a *required* check but the matrix is empty for a PR that touched no image, the check never reports and the PR can never merge. So the *required* check is a final `gate` job — `needs: [detect, build-test]`, `if: always()` — that passes when nothing was built and fails only if a matrix leg failed. The matrix job itself is never the required check.

**Build caching.** Each affected build runs cold otherwise. Pass `cache-from`/`cache-to: type=gha` (or a registry cache tag) as bake overrides for layer reuse — the cheap 80% of "incremental builds" without adopting a build-graph tool.

### 4. Releases — two tiers

**Tier 1 — per-app product release.** Each app has its own semver, changelog, and tag prefix (`warden-v1.4.0`). For v1 this is a **manual tag cut** — simplest, no new tooling, and it respects the existing no-scope commit style. Automating version bumps from commits (via `release-please`, which maps commits to components by changed path) is a later, optional step.

**Promote, don't rebuild.** The tag job does *not* rebuild from the tag's source — it retags the already-built-and-tested `:<sha>` image to `:X.Y.Z` (`docker buildx imagetools create` / `crane tag`). Rebuilding risks a different artifact than the one CI tested (base-image drift, transient deps). Released must equal tested.

**Version source of truth: the git tag.** The tag is authoritative; the app's `pyproject.toml`/`package.json` version is cosmetic and need not match. (If you later adopt `release-please`, it makes the manifest file authoritative instead — one switch, not a mix.)

**Tier 2 — homelab platform release.** Becomes a bill of materials: it records which app versions ship and is what actually changes production. The existing weekly `python-semantic-release` continues to version the platform (infra, compose wiring, docs).

**The pin is a literal tag in compose, tracked in git.** Compose used `${WARDEN_IMAGE_TAG:-…}` sourced from `.env`, and `.env` is never committed (synced to Bitwarden) — so the deployed version was invisible to the repo and not reproducible. The fix needs no new file and no env var: write the released semver as a literal —

```yaml
image: ${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE}/warden:1.4.0
```

— so the deployed version is in version control and reproducible. Dropping the `*_IMAGE_TAG` var makes "`.env` is not the version source" structurally true: there is no override knob to misuse. A Tier-1 release bumps that literal in the app's compose; the Tier-2 release is the aggregate diff of those bumps. (A central `versions.yaml` BOM is a *later, optional* convenience if "what version is everything?" becomes a frequent question — it adds deploy wiring to read it, so it is not in the base plan.)

### 5. The shared devbox Dockerfile

`images/devbox/` is a shared `Dockerfile`, not a unit. `claudecodeui` and `code-server` intentionally share one `homelab-devbox` environment (same source tree + ssh dirs — see the rstudio compose comments), so each builds from that Dockerfile (§1) with `images/devbox/**` in its `x-homelab.watch`. A change to the Dockerfile flags both consumers through ordinary fan-out (§2); since both resolve to the same `homelab-devbox` image, CI builds it once and both stacks redeploy it.

There is no separate devbox unit, no cross-image graph, and no `consumers:` list to maintain. This also retires the old manual flow (build/push `homelab-devbox` by hand, then hand-edit the `@sha256:` digest in each consumer): CI builds the shared image like any other, and the consumers pick it up from the same pipeline — so devbox stops being the one image that's pinned differently from the rest of the repo.

### 6. Testing — one structure, structurally detected

Tests are not declared anywhere — they're discovered from the filesystem, because every buildable app already follows the same layout:

```
<project root>/        # the build context (or a subdir of it, e.g. app/)
  Dockerfile
  pyproject.toml        # has a [dependency-groups] dev group with pytest
  tests/
    unit/               # fast PR gate
    integration/        # run if present
    e2e/                # run if present — pytest, like the other tiers
```

The contract, which is ~95% already true in the repo:

- **A testable project = any dir with a `pyproject.toml`** under `stacks/**` (minus the repo root and `.venv`). Each declares its test deps in a `[dependency-groups]` dev group, so `uv run pytest` self-bootstraps — no install step.
- **Tiers are directories, not config.** The runner runs what exists: `tests/unit` (always, the gate), then `tests/integration`, then `tests/e2e` — all via `uv run pytest <dir>`. fiber's three tiers are just three subdirs; no manifest expresses them, and there is no per-app shell entrypoint.
- **`lint-imports` is a lint, not a test.** A project with `[tool.importlinter]` (fiber, warden) runs `uv run lint-imports` in the lint phase — that's why warden's old `pytest && lint-imports` splits cleanly across phases.
- **The JS frontend has no test suite** (`takeout-manager/manager/frontend` is vite `dev`/`build`/`preview` only), so it's gated by `vite build` inside the manager Dockerfile. No polyglot test detection needed.

Running tests is the `ci test` subcommand of the `tools/ci` package (not a separate shell script — repo tooling with real logic lives in one tested CLI). It discovers `pyproject.toml` dirs under `stacks/`, selects by name/path, and runs `uv run pytest tests/<tier>` for whichever tier dirs exist; the unit tier keeps the project's coverage gate, integration/e2e clear it. The selection logic is unit-tested. Local (`task test*`) and CI (`uv run ci test <context>` in the build matrix) call the identical command. **Compose carries no test config at all.**

Local ergonomics (thin Taskfile wrappers over the same script):

```
task test                       # all tiers, all buildable apps
task test -- warden             # all tiers for one app (takeout-manager → manager + worker)
task test:unit -- warden        # one tier, one app
task test:integration -- fiber
task test:e2e -- fiber
task test:affected              # only apps changed vs main (reuses affected.py)
```

(Task forwards args only after `--`, so the app name follows `--`.) The former shell-test `task test` — the bats/kcov suite — moves to `task test:shell`, and `task check` runs `lint` + `test:shell` + `test` (apps) + `docs:validate`.

Normalization to land the contract (small, mechanical):

- **Convert fiber's `tests/e2e/run-e2e.sh` to a pytest module** (`tests/e2e/test_*.py`) that drives the existing `compose.yml`/`seed.sql` (via testcontainers' `DockerCompose` or `subprocess`) and asserts in Python. It consumes the image the matrix already built (image ref via env), rather than rebuilding. This removes the runner's only shell-script special case, so every tier is `uv run pytest <dir>`. (Good moment to keep true black-box-image e2e in `tests/e2e` and leave testcontainers tests in `tests/integration`.)
- `custom-exporter`: move its flat `tests/*.py` into `tests/unit/` (and `tests/integration/` for `test_integration.py`) to match the tier convention.
- Route `lint-imports` into the lint phase for the two projects that declare import contracts.
- (Already true, just assert in the schema/discovery: every buildable `pyproject.toml` has the dev group + `[tool.pytest.ini_options]`.)

### 7. Env-var consistency

The registry host and namespace are the same for the whole repo; only the image *tag* varies per app (because apps release independently). Today every app duplicates the host and namespace anyway, with three different defaults. Make the shared parts global and keep only the tag per app:

| Concern | Today | Proposed |
| --- | --- | --- |
| Registry host | per-app `WARDEN_REGISTRY_URL`, `FIBER_REGISTRY_URL`, bare `REGISTRY_URL`, … | one global `REGISTRY` (default `ghcr.io`) |
| Namespace | three defaults across apps: `chutch3`, `your-username`, `.GITHUB_USERNAME` | one global `REGISTRY_NAMESPACE` (single default) |
| Image name | env var (`IMAGE_NAME`) or implied by the Taskfile | the compose service's `image:` — declared once, where it already lives |
| Tag | per-app `*_IMAGE_TAG` env var (from `.env`) | a literal released semver in the compose file — no env var (§4) |

Compose then reads:

```yaml
image: ${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE}/warden:1.4.0
```

This removes the `kolibri` / `devbox` bare-`REGISTRY_*` collision with the global namespace (they no longer own those names), drops ~2 env vars per app from `.env.example`, and leaves one source of truth for "where images live".

### 8. Delete the duplicated Taskfiles

The 5–6 near-identical per-app `build`/`push`/`publish` Taskfiles exist only because each hardcodes its image name, context, and dockerfile. With `build:` in compose (§1), `docker buildx bake` already does all of that — context, dockerfile, platforms, cache, tags — so no `build.py` or per-app Taskfile is needed. A thin root wrapper is the only local entry point:

```
task build -- warden        # docker buildx bake -f stacks/apps/warden/docker-compose.yml warden
task publish -- warden      # bake with --push
```

Local and CI then build identically (both call bake on the same compose file). The per-app `Taskfile.yml`s under `warden/`, `fiber/`, `takeout-manager/`, `kolibri/`, `monitoring/`, and `images/devbox/` are deleted, and the root `Taskfile.yml` `includes:` block for them collapses. Their `test:` tasks aren't ported anywhere — testing is the convention in §6.

**The general pattern — one CLI surface for per-unit verbs.** `build`/`publish`, `test` (§6), per-app `lint`, and `deploy` all take the same shape, because they all start from the same `discover_units`:

```
task <verb>                 # all units
task <verb> -- warden       # one unit (multi-image apps fan out)
task <verb>:affected        # only units changed vs main (reuses affected.py)
```

The discipline: **the Taskfile entry is a thin `{{.CLI_ARGS}}` forwarder; the logic lives in a tested `tools/ci` script that CI calls too.** The Taskfile is a discoverable CLI surface, not a place behavior hides — the opposite of the per-app Taskfiles being deleted. This applies to *per-unit* verbs only; genuinely global tasks (`setup`, `install`, `docs:*`, `secrets:*`, `release:*`, `registry:login`, and the cross-cutting yaml/shell/dockerfile/gitleaks linters) stay as-is. Aligning `task deploy -- warden` with the existing `ansible:deploy:service` gives one `-- <app>` convention across build/test/lint/deploy.

### 9. Adjacent cleanups

Not strictly build/release, but cheap to fix in the same pass and currently misleading:

- **`task check` exercises none of the apps.** Today `task test` / `task check` run only the 6 bats/kcov shell tests; the Python suites (`fiber`, `warden`, `takeout-manager/{manager,worker}`, `custom-exporter`) are never run locally. The §6 reorg fixes this: the bats suite becomes `test:shell`, `task test` becomes the app runner, and `check` runs both — so local matches CI (§3).
- **Python version drift.** `Taskfile.yml` pins `PYTHON_VERSION: "3.9"`, root `pyproject.toml` requires `>=3.10`, the apps require `>=3.12`. The Taskfile var is stale; align the three.

### 10. Pre-commit interaction

The config already has the right precedents: a `check-jsonschema` hook validating `pre-flight.yml`, and `ansible-preflight-unit` running scoped tests (`files:` regex, `uv run --frozen`) only on relevant changes. The plan extends, doesn't rework, it:

- **`x-homelab` validation is a local hook, not a schema file.** The shape could be `check-jsonschema`, but the `watch ⊇ build.context` invariant is a cross-field rule (and `context` is compose-relative vs `watch` repo-relative) that JSON Schema can't express. So validation is a local hook backed by `tools/ci` `discover_units` — shape + invariant in one tested place, scoped to `docker-compose\.ya?ml$`.
- **Add the missing Python lint.** Pre-commit runs no Python linter today (only shell/yaml/dockerfile/secrets). The §8 `lint` verb lands here as a local hook scoped to changed app paths — `ruff` + `lint-imports` (for projects with `[tool.importlinter]`).
- **App `pytest` stays out of pre-commit by default** — unit/integration/e2e run in CI per affected unit; keeping commits fast. (The `ansible-preflight-unit` precedent means running the `unit` tier here scoped + `--frozen` is an option if wanted; lean to a `pre-push` hook over per-commit.)
- **No change needed** for `hadolint` (covers the shared devbox Dockerfile), `yamllint`/`check-yaml`/`gitleaks`/`detect-private-key` (cover the new `build:` blocks) — the only obligation is to author the new YAML to pass `yamllint`.
- **Dual-run for enforcement.** The new `x-homelab` and lint hooks run in *both* pre-commit and the CI `detect`/lint job (as `hadolint`/`gitleaks` already do), so skipping pre-commit can't bypass them.

### 11. Docs / GitHub Pages CI

`docs.yml` runs only via `workflow_call` (from `release.yml`, on a cut release) or manual dispatch — it has **no `push`/`pull_request` trigger**, so despite the `validate` job's "on PRs and pushes" comment, docs are never built on a PR. A PR that breaks the mkdocs build isn't caught until the weekly release tries to deploy; nothing else covers it (`ci-cd.yml` runs `lint`/`static-analysis`, not `docs:validate`). Same shape as the app-test gap, in the docs lane.

- **Add a PR/push docs gate**, path-filtered to docs sources (`docs/**`, `mkdocs.yml`, `llms.txt`, `docs/includes/**`): run `task docs:validate` (or `docs:validate-strict` to catch nav/orphan/broken-link warnings) so a broken build fails the PR, not the release.
- **Decouple deploy from release (recommended for a homelab):** deploy on push to `main` when docs change, so fixes publish promptly. Keep release-coupling only if published docs should snapshot the platform release.
- **Keep the path-filtered docs check non-required** (same empty-result deadlock as §3), or wrap it like the `gate`.
- Fix the misleading `validate`-job comment. Docs stays its own workflow (mkdocs + Pages target — not folded into `build.yml`).

## Gotchas & mitigations

Recap of the failure modes this design has to handle (most are addressed inline above):

| Gotcha | Mitigation | Where |
| --- | --- | --- |
| Path-filtered required check deadlocks branch protection | Always-run `gate` job is the required check, not the matrix | §3 |
| Pin lives in untracked `.env` → non-reproducible deploy | Released semver is the committed compose default; `.env` is not the source | §4 |
| `watch` narrower than `build.context` → silent stale image | `watch` defaults to whole stack dir; schema check enforces `watch ⊇ build.context` | §1 |
| Build-tooling change matches no unit → ships to nothing | Tooling paths mark all units affected | §2 |
| Shared-file change must rebuild every dependent | `affected_units` is many-to-many; shared image dedups by ref (build once) | §1/§2 |
| Wrong diff base → builds nothing or everything | `fetch-depth: 0`; base per event with all-zeros fallback to build-all | §2 |
| Tag rebuild ≠ tested image | Promote `:<sha>` to `:X.Y.Z`, don't rebuild | §4 |
| `:<sha>`/`:main` tags accumulate in ghcr forever | Scheduled cleanup (`actions/delete-package-versions` or ghcr retention), keep tagged releases | new workflow |
| Malformed `x-homelab` / `watch` ⊅ `context` discovered late | Local `validate.py` (shape + invariant) in pre-commit *and* the `detect` job | §1/§10 |

## Changes

### New files

| Path | Purpose |
| --- | --- |
| `tools/ci/` (the `ci` project, installed editable via root) | `ci.affected` (compose discovery, fan-out, image dedup) + `ci.apptests` (`pyproject` discovery, tier selection) behind one `ci` CLI (`ci affected`, `ci test`); fully unit-tested |
| `.github/workflows/build.yml` | `detect` → `build-test` matrix (`buildx bake` + gha cache) → always-run `gate`; PR builds no-push, main pushes `:sha`/`:main`, tag promotes to semver |
| `.github/workflows/ghcr-cleanup.yml` | Scheduled pruning of old `:<sha>`/`:main` images; keep tagged releases |
| `tools/ci/ci/validate.py` (+ optional `schemas/x-homelab.schema.json` for shape) | Local validator reusing `discover_units`: `x-homelab.watch` shape **and** the `watch ⊇ build.context` invariant (cross-field → not pure JSON Schema). Run by pre-commit + the `detect` job |
### Modified files

| Path | Change |
| --- | --- |
| `.github/workflows/ci-cd.yml` | Keep global lint; remove any per-app responsibility it implies |
| `.github/workflows/docs.yml` | Add a path-filtered `pull_request`/`push` trigger so docs build on PRs (§11); optionally decouple deploy from release; fix the stale "on PRs" comment |
| `.github/workflows/fiber-tests.yml` | Fold into `build.yml` (fiber becomes one matrix entry); delete once parity is confirmed |
| `stacks/apps/*/docker-compose.yml` (buildable apps) | Add `build:` (+ `x-homelab.watch` only where the default doesn't cover it); image ref → global `${REGISTRY}/${REGISTRY_NAMESPACE}/<image>:<literal semver>` — drop the `*_IMAGE_TAG` var and `:latest` |
| `stacks/apps/{claudecodeui,code-server}/docker-compose.yml` | Add `build:` pointing `dockerfile` at the shared `images/devbox/Dockerfile` + a duplicated `x-homelab` whose `watch` includes `images/devbox/**`; CI builds `homelab-devbox` instead of manual digest pinning |
| `images/devbox/` | Keep just the `Dockerfile`; its Taskfile is deleted (built via the two consumers) |
| `stacks/apps/fiber/app/tests/e2e/` | Replace `run-e2e.sh` with a pytest module driving the existing `compose.yml`/`seed.sql`, consuming the pipeline-built image; e2e becomes a normal `uv run pytest tests/e2e` tier |
| `stacks/monitoring/custom-exporter/tests/` | Move flat `tests/*.py` into `tests/unit/` (+ `tests/integration/`) to match the §6 tier convention |
| `fiber`/`warden` lint config | Route `lint-imports` (import-linter) into the lint phase, out of the test command |
| `Taskfile.yml` (root) | Drop the per-app `includes:` block; add `build`/`publish` (`buildx bake`) wrappers and `test`/`test:unit`/`test:integration`/`test:e2e`/`test:affected` (shell: glob `pyproject.toml` dirs → `uv run pytest` by tier — CI calls these same tasks); rename the old bats `test` → `test:shell`; rewire `check` = `lint` + `test:shell` + `test` + `docs:validate`; fix stale `PYTHON_VERSION` |
| `.env.example` | Collapse per-app `*_REGISTRY_URL`/`*_REGISTRY_NAMESPACE` into global `REGISTRY`/`REGISTRY_NAMESPACE`; remove per-app `*_IMAGE_TAG` (tag is the committed compose literal) |
| `pyproject.toml` (root) | Align Python version with the Taskfile var and the apps |
| `.pre-commit-config.yaml` | Add local hooks for `x-homelab` validation (`validate.py`) and per-app Python lint (`ruff` + `lint-imports`), scoped via `files:`; mirrors the existing `pre-flight`/`ansible-preflight-unit` hooks (§10) |

### Removed

- The 5–6 near-identical per-app `Taskfile.yml`s (`warden`, `fiber`, `takeout-manager`, `kolibri`, `monitoring`, `images/devbox`) — build/push logic is now `docker buildx bake` driven by each compose file's `build:` section. No `build.py`.
- Per-app `*_REGISTRY_URL` / `*_REGISTRY_NAMESPACE` env vars and the three conflicting namespace defaults — replaced by global `REGISTRY` / `REGISTRY_NAMESPACE`.
- Per-app `*_IMAGE_TAG` env vars — the released tag is a committed literal in compose (§4).

## Rollout

The structural change lands as **one PR** — there is no stakeholder big-bang to de-risk, and partial states (e.g. `build:` with no CI, or deleted Taskfiles before bake works) are worse, not safer. "Prove the affected logic first" isn't a phase; it's the unit tests, written test-first within the PR since that logic is the one silent-failure-prone piece.

**The one PR** (all interdependent, review and CI-validate together):

- `build:` in every buildable compose (+ `x-homelab.watch` only for the two devbox consumers); literal image refs via global `${REGISTRY}/${REGISTRY_NAMESPACE}`.
- `tools/ci/ci/affected.py` + its unit tests (fan-out, image dedup).
- `.github/workflows/build.yml` — landed **non-required**: `detect` → `build-test` (bake + gha cache) → always-run `gate`.
- Delete the per-app Taskfiles; add the `build`/`publish`/`test*` shell tasks; rename bats `test`→`test:shell`; rewire `check`.
- Normalize: `custom-exporter` tiers, `lint-imports`→lint, fiber `e2e`→pytest; fix the `PYTHON_VERSION` drift; retire `fiber-tests.yml`.

**Then a short enablement sequence** — the only genuinely ordered steps, because each depends on the previous existing:

1. On the PR, watch `build.yml` produce correct affected matrices and green builds. Merge.
2. **Flip `gate` to a required check** in branch protection — *after* step 1, or the empty-matrix deadlock (§3) locks merges.
3. Cut the first per-app release tags → CI promotes `:sha`→semver → **update each compose pin off `:latest` to the literal semver**. This must follow, since you can't pin a version CI hasn't built yet.

**Optional, never in the critical path:** `validate.py` (when `x-homelab` usage grows), `ghcr-cleanup.yml` (or just ghcr UI retention), `release-please`, a `versions.yaml` BOM, and CD that dispatches `task ansible:deploy:service` via the `github-runner` stack.

## Open decisions

- **Release cut: manual tag vs `release-please`.** Plan assumes manual for v1; revisit if cutting tags by hand becomes a chore.
- **Pin location is settled:** literal semver in each compose file (no env var, not `.env`). A central `versions.yaml` BOM stays an optional later add if a one-glance platform view is wanted (it needs deploy wiring to read it).
- **Pin granularity:** semver tag vs immutable digest (devbox uses digests; matching that everywhere is stricter but noisier to bump).
- **Multi-arch:** confirm whether all swarm nodes are `linux/amd64`. If yes, single-arch is correct and no `platforms` override is needed. If any node is arm, set `platforms` on those images and budget the longer buildx builds.

## Out of scope

- **Relocating buildable apps to a top-level `apps/`.** It would clarify the two-lifecycle split but touches every compose path, ansible `stack_name` lookup, and CI filter. The manifest convention gets ~90% of the clarity without the churn; defer unless the split proves painful.
- A dependency-graph build system. Reconsider only if shared/base images multiply beyond the single devbox edge.
