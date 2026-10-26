# Portable profile catalogs — bootstrap, comparison, and observation

Implemented: local YAML/JSON validation, a read-only dump of current Arr quality
profiles and referenced custom formats, semantic diff, and scheduled observation
from Git or a read-only directory. These features use the existing Arr HTTP
clients. Standalone commands do not start Warden's server, hunter, or SQLite database.

The schema is an initial version under development. Read-only dump and diff have
been exercised against Radarr 6.1.1.10360 and Sonarr 4.0.20.3014: 29 profiles and
398 custom formats exported, validated, and compared cleanly. This does not certify
other API versions or future write operations. Tests also exercise HTTP contract
fixtures and local files.

## Run from the source checkout

```bash
cd stacks/apps/warden/app
uv run python -m warden.profiles.cli validate --directory ../examples/profiles

# Supply these through your existing secret/environment setup:
export WARDEN_RADARR_URL=http://radarr:7878
export WARDEN_RADARR_API_KEY='<your-api-key>'

# Choose a directory on a verified local filesystem.
uv run python -m warden.profiles.cli dump --source radarr --output /local/media-profiles
uv run python -m warden.profiles.cli dump --source sonarr --output /local/media-profiles
uv run python -m warden.profiles.cli dump --source radarr --profile HD --output /local/selected-profiles
uv run python -m warden.profiles.cli validate --directory /local/media-profiles
uv run python -m warden.profiles.cli diff --source radarr --directory /local/media-profiles
uv run python -m warden.profiles.cli diff --source radarr --directory /local/media-profiles --json
```

Sonarr uses `WARDEN_SONARR_URL` and `WARDEN_SONARR_API_KEY`. Dump defaults to all
profiles on that source; repeat `--profile` to select exact names. It reads only
the quality-profile and custom-format endpoints. The proposed installed
`warden-profiles` console command is not packaged yet; use the module command above.
Dump/validation success exits 0; failures exit 1. Diff exits 0 for clean/disabled,
2 for drift, and 1 for errors or shared-format conflicts. Invalid command syntax
exits 2, so automation should invoke a known command and check stderr as well.

## Test a dump before deployment, without Docker

The source CLI can export and compare profiles directly from this machine. Set
the Arr URLs to addresses reachable from this machine; Swarm-only names such as
`http://radarr:7878` generally require using an external URL or an SSH tunnel here.
Supply API keys through the environment.

Choose a verified local destination. The homelab development workspace itself is
on OCFS2, so it is rejected as a dump destination. For a temporary Linux test:

```bash
catalog_dir="$(mktemp -d /dev/shm/warden-profiles.XXXXXX)/catalog"
uv run python -m warden.profiles.cli dump --source radarr --output "$catalog_dir"
uv run python -m warden.profiles.cli dump --source sonarr --output "$catalog_dir"
uv run python -m warden.profiles.cli validate --directory "$catalog_dir"
uv run python -m warden.profiles.cli diff --source radarr --directory "$catalog_dir"
uv run python -m warden.profiles.cli diff --source sonarr --directory "$catalog_dir"
```

Run these from `app/`. Edit one exported score and repeat diff: it should report
that change and exit 2. Restore the file and diff should exit 0. These operations
only read Arr; they do not start Warden's hunter or modify Arr configuration.
Quality groups may have the same label as one of their members; repeated actual
qualities or duplicate top-level group labels remain invalid.

`/dev/shm` is memory-backed and temporary. Preserve a verified export on appropriate
durable storage before restarting this workspace. Both the standalone CLI and
the daemon's directory mode accept these plain files without a Git repository.

## Run the observer against a local directory

Set `WARDEN_PROFILES_DIRECTORY` to the absolute catalog directory and leave
`WARDEN_PROFILES_REPO` unset. Setting both is an error. For example:

```dotenv
WARDEN_PROFILES_DIRECTORY=/profiles/catalog-example
WARDEN_PROFILES_MODE=observe
WARDEN_PROFILES_INTERVAL_SEC=900
```

Directory mode re-reads and validates the catalog on each cycle, using the same
filters, comparison, metrics, and error handling as Git mode. It creates no Git
repository, profile cache, backups, or database. The existing
`WARDEN_PROFILES_CACHE_MAX_BYTES` limit also bounds catalog bytes read in this mode
(32 MiB by default). Logs identify directory snapshots as `directory:<SHA-256>` in
the existing `commit` field. Invalid edits fail the check while retaining the last
observed drift. Prefer complete, immutable catalog directories for deployment;
editing multiple files in place can expose an intermediate catalog to a check.

For a standalone container, bind-mount the exported catalog read-only and set
`WARDEN_PROFILES_DIRECTORY` to that mount. Starting `warden.main` also starts the
normal hunter; use the standalone `diff` command for a read-only pre-deployment
check against production Arr.

The Swarm stack mounts the node-local `warden_profiles` volume read-only at
`/profiles`. Copy the same verified catalog into that volume on every eligible
node before enabling the directory setting. Use a revision-specific subdirectory,
then set the environment path to it. Node-local catalogs must be provisioned again
when adding a new node; an empty catalog fails observation visibly. Git mode does
not use this volume. Catalog files are static configuration on each node's local
Docker storage; Warden never modifies them.

## Compare local intent with Arr

Diff uses the local catalog as desired state and current Arr API responses as
actual state. A dump compared with the unchanged HTTP contract fixture is clean.
Changing one desired score from 100 to 250 gives:

```text
radarr: 1 change across 1 resource.
  profile "HD": custom_format_scores.Preferred: 100 -> 250
```

With `--json`, the same comparison produces:

```json
{
  "source": "radarr",
  "profiles": ["HD"],
  "changes": [
    {
      "kind": "profile",
      "name": "HD",
      "field": "custom_format_scores.Preferred",
      "current": 100,
      "desired": 250
    }
  ],
  "conflicts": []
}
```

The default selection is all catalog profiles for the specified application.
`WARDEN_RADARR_PROFILES` / `WARDEN_SONARR_PROFILES` can provide a JSON array of
exact names. `[]` disables comparison for that source without contacting Arr.
Repeatable `--profile` arguments override that environment filter. Empty strings,
malformed arrays, unknown names, or implicit-all with no compatible profiles are
errors before any API request.

The comparison covers selected profiles and the custom formats they reference.
Remote IDs, mapping order, condition order, documentation, and community provenance
do not create drift. Quality precedence and group-member order remain meaningful.
Omitted `enabled` means true; omitted Radarr `language` leaves language unmanaged.
Within a managed profile, an omitted custom-format score means zero. Unrelated
remote zero-score entries therefore produce no drift, while a nonzero score omitted
locally is shown changing to zero. No custom-format deletion is proposed.

A missing remote resource has `field: "$"`, `current: null`, and its desired
configuration. Arrays with meaningful ordering are reported as whole-field
changes. The JSON report is a comparison representation, not an Arr API payload
or an executable patch. Field paths are display labels. A renamed local profile
appears as a new resource; the previous remote profile and media assignments remain
outside this plan.

Changing a shared custom-format definition reports every unselected remote profile
whose score list references it, conservatively including zero-score references.
Such a conflict exits 1 and appears in the `conflicts` array (or human output).
Include all affected profiles in the catalog/selection, or use a separately named
custom format. A failed read or invalid response exits 1 with a diagnostic on
stderr and no clean/partial report on stdout. Diff makes no mutations or catalog
writes, and has no cache, backup, or SQLite dependency.

## Observe a Git repository in Warden

The normal Warden service starts an independent observation loop when either
profile source is set. The observer never applies changes or triggers searches.
The existing hunt loop keeps running independently, including when profile
configuration, Git access, catalog validation, or Arr reads fail.

```dotenv
WARDEN_PROFILES_REPO=https://github.com/you/media-profiles.git
WARDEN_PROFILES_REF=main
WARDEN_PROFILES_PATH=.
WARDEN_PROFILES_MODE=observe
WARDEN_PROFILES_INTERVAL_SEC=900
WARDEN_PROFILES_TIMEOUT_SEC=60
WARDEN_PROFILES_CACHE_MAX_BYTES=33554432
# Optional exact selections; omitted selects all and [] disables a source:
# WARDEN_RADARR_PROFILES='["HD"]'
# WARDEN_SONARR_PROFILES='[]'
```

The image includes Git and OpenSSH for fetching repositories. When running from
source, install Git and (for SSH remotes) OpenSSH on the host. `MODE=sync`
is rejected; observation is the only implemented daemon mode. Restart the service
to change environment settings. The standalone diff command still requires a
local `--directory`; daemon repository configuration does not yet make the CLI
fetch Git automatically.

The image starts its installed Python environment directly, without downloading
development dependencies at startup. To check a built image, run this from `app/`:

```bash
WARDEN_TEST_DOCKER_CONTEXT=homelab \
WARDEN_TEST_IMAGE='ghcr.io/chutch3/warden:<prerelease-tag>' \
uv run pytest tests/e2e/test_image.py --no-cov
```

This opt-in check starts a temporary container with networking disabled and state
and profile cache on tmpfs. It verifies health, SSH availability, and a local Git
catalog fetch, then removes the container. It never contacts live Arr instances.

`REF` accepts a branch, tag, qualified ref, or full commit hash. A named ref resolves
once per cycle; that exact commit supplies all targets in the cycle. Ambiguous
branch/tag names require `refs/heads/...` or `refs/tags/...`. `PATH` selects a
subdirectory inside the checkout. The whole shallow checkout, including Git
metadata and candidate staging, counts against the cache budget. Use a dedicated
catalog repository rather than a large monorepo.

Unchanged revisions reuse the parsed snapshot without checkout writes. A changed
revision must fetch and validate completely before replacing the active snapshot.
An invalid or unreachable candidate marks checks failed and leaves the last valid
snapshot and observed drift available; it does not compare stale desired state
and report a new success. Arr is re-read on every successful observation cycle.
Git reverts and manual Arr fixes can therefore clear drift.

The Compose configuration declares `/profile-cache` as a 64 MiB tmpfs mount,
separate from `/state`. The application budget defaults to 32 MiB, including both
the current snapshot and staging, with an additional 10,000-entry bound. Git output
and execution time are bounded; cancellation kills Git's process group. Disk usage
is checked during Git commands, so transient usage can exceed the application
budget before cancellation; the tmpfs mount supplies the hard storage bound.
Tmpfs uses container memory, so catalog size and process memory must fit the
existing 256 MiB service limit. Large-catalog benchmarking is still pending.

When running from source, set `WARDEN_PROFILES_CACHE_DIR` to a dedicated empty
absolute directory on verified local storage. Shared paths `/state` and
`/mnt/iscsi`, symlink paths, and shared/unknown filesystem types are rejected before
cache mutation. Only marked Warden cache directories are adopted; snapshots left
by a killed process are rebuilt on restart. Use one observer per cache directory.
No manual backup cleanup, shared SQLite writes, or persistent profile database
are involved in profile observation. The existing hunter's SQLite state is separate.

Repositories may use HTTPS, SSH (including `git@host:path`), or absolute local/file
paths. Credentials must stay outside repository URLs and catalog files. For private
HTTPS, provide credentials through an external `GIT_ASKPASS` helper. For SSH,
provide an agent or normal SSH identity/config and pre-provisioned known hosts.
Interactive prompts are disabled and SSH host-key checking is strict. Global/system
Git configuration is disabled for snapshot operations; SSH configuration and
explicit credential helper environment remain available. Git stderr and repository
URLs are not logged. Checkout hooks, automatic Git GC, and submodule initialization
are not used.

Observation adds these metrics to the existing `/metrics` endpoint:

| Metric | Meaning |
|---|---|
| `warden_profiles_enabled{source}` | Observation enabled for a configured Arr target. |
| `warden_profiles_check_success{source}` | Whether the last complete comparison succeeded. |
| `warden_profiles_last_successful_check_timestamp_seconds{source}` | Time of that successful comparison. |
| `warden_profiles_drift_resources{source,kind}` | Last known count of changed or missing profiles/custom formats. |
| `warden_profiles_conflicts{source}` | Last known shared-format conflicts. |
| `warden_profiles_drift_since_timestamp_seconds{source}` | First observed unresolved drift; zero when clean. |
| `warden_profiles_interval_seconds{source}` | Configured interval, used by alert timing. |
| `warden_profiles_started_timestamp_seconds{source}` | Startup baseline for never-successful targets. |
| `warden_profiles_cycle_duration_seconds` | Observation-cycle duration histogram. |

A failed check sets success to zero without resetting previous drift or freshness.
Conflicts are valid comparison results and remain visible as drift plus conflict
counts. Logs identify resolved commits, selected profiles, and detailed changes;
metric labels contain only the bounded source/kind values.

Prometheus rules in `stacks/monitoring/prometheus/alert-rules.yml` provide:

- `WardenProfilesDrift`: unresolved drift for one configured interval, gated by a
  successful check whose age is less than two intervals.
- `WardenProfilesCheckFailed`: enabled target with failed checks for five minutes.
- `WardenProfilesStale`: no successful comparison in two intervals, with the same
  startup grace for targets that have never succeeded.

Disabled targets do not alert. Tests cover Git changes, invalid candidates,
repository outages, recovery, continued hunting, timeout cleanup, and alert states.
Validate rules with the deployed Prometheus version's `promtool test rules
warden-profiles.test.yml alert-rules.test.yml` from the Prometheus directory.

## Catalog layout

```text
media-profiles/
  radarr/
    profiles/HD.yml
    custom_formats/Preferred.json
  sonarr/
    profiles/HD.yml
    custom_formats/Preferred.json
```

Files can have any name and can be grouped in subdirectories beneath these four
locations. `.yml`, `.yaml`, and `.json` files are read. Other files, such as READMEs,
are ignored. Application scope comes from the directory. Names match exactly and
are unique within each application; Radarr and Sonarr can both have a profile
called `HD`. Symlinks within the catalog are rejected. No central manifest or
Profilarr metadata is required.

Dump emits one file per profile/format, using percent-encoded resource names as
filenames. It retains quality precedence, group membership, upgrade settings,
score thresholds, scores, and Radarr language. Remote resource IDs are resolved
to names. It cannot recover comments, upstream history, or provenance absent from
the instance. All custom formats referenced in the profile's score list are
exported, including zero-score entries.

## Profile YAML

The [profile schema](app/warden/profiles/schemas/profiles-v1.json) defines the
complete supported structure. The [example catalog](examples/profiles) is valid
input; its values are illustrative.

```yaml
schema_version: 1
quality_profiles:
  - name: HD
    upgrade:
      allowed: true
      until_quality: WEB 1080p
      until_score: 1000
    min_format_score: 0
    min_upgrade_format_score: 1
    qualities:
      - name: WEB 1080p
        qualities: [WEBDL-1080p, WEBRip-1080p]
    custom_format_scores:
      Preferred: 100
```

The profile vocabulary follows a subset of
[Recyclarr's documented fields](https://recyclarr.dev/reference/configuration/quality-profiles/).
The `schema_version` envelope and name-keyed `custom_format_scores` mapping are
Warden extensions. This is not a full Recyclarr or Configarr configuration parser.

All behavioral fields shown above are required. Partial update templates must be
resolved into explicit values first; missing fields do not imply remote defaults.
`enabled` defaults to true for a quality/group. Qualities are ordered highest
preference first; dump reverses Arr's API list to preserve this convention.
The cutoff must name an enabled top-level quality or group. Group members retain
their order and cannot also appear elsewhere in the same profile. Mixed enabled
states within an imported group are rejected instead of flattened.

`custom_format_scores` explicitly lists the profile's desired assignments, and
every named format must exist in that application's catalog. Scores are signed
32-bit integers; booleans, fractions, and numeric strings are rejected. Optional
`description` is documentation. Optional `language` is a portable Radarr language
name; Sonarr profiles reject it. Dump includes Radarr's effective language.

Unknown fields, unsupported schema versions, duplicate YAML keys, duplicate
resource names, and missing references produce an error identifying the file and
field or resource. JSON Schema editors can use the local schema file directly.

## Custom-format interoperability

The [custom-format schema](app/warden/profiles/schemas/custom_formats-v1.json)
accepts Arr-style definitions with `name`, `includeCustomFormatWhenRenaming`, and
`specifications`. Each specification supplies a name, implementation, negate/required
flags, and fields. Fields can use the export object form (`{"value": "pattern"}`)
or the API list form (`[{"name": "value", "value": "pattern"}]`). Dump writes the
export object form. JSON and YAML serialize the same structure.

The optional `trash_id` and `trash_scores` metadata fields are retained when reading
community files. They never implicitly change profile scores. Other unrecognized
metadata currently fails validation. This follows the interchange approach used by
[TRaSH custom-format imports](https://trash-guides.info/Sonarr/sonarr-import-custom-formats/);
there is no automatic upstream lookup.

Local validation checks structure and references. It does not yet query a target
application's supported condition implementations, quality names, or languages.
An accepted file is not a promise that a particular Arr version can apply it.
Unknown remote profile/quality fields fail dump, including per-quality size
settings that this increment cannot represent. Review diagnostics before using
an export for migration.

## Output and storage behavior

Dump stages and validates the complete merged catalog before publishing files.
Existing identical files keep their contents and modification times. Differing
files or duplicate resource names across different filenames fail without
publishing the candidate. Publication creates files without overwriting existing
ones. It is not an atomic multi-file transaction: interruption can leave a partial
export; rerun to complete identical files, or resolve a reported collision.

On Linux, dump checks `/proc/self/mountinfo` and rejects OCFS2, network filesystems,
overlay, and unknown filesystem types for output/staging. The allowlist is ext4,
XFS, Btrfs, and tmpfs; nested mounts and bind-mount filesystem types are considered.
Confirm the allowed backing storage is node-local before using it: the filesystem
type alone cannot prove the physical device's ownership or topology. Use a local
host directory rather than container overlay storage. There is no bypass flag.

The utility has no periodic backup or retention job. Temporary export data is
cleaned only from the checked local staging location. It does not access Arr data
directories or Warden's shared state. This avoids introducing the observed OCFS2
backup-cleanup workload; it does not establish or repair the cause of the incident.

## Remaining increments

- Legacy Profilarr import and a documented community-template conversion matrix.
- Broader API-version certification beyond the verified Radarr/Sonarr versions above.
- Installable CLI packaging.
- Private-remote checks and resource benchmarks.
- Safe synchronization, conflict handling, partial-failure recovery, and read-back.

The homelab deployment was verified with the exported catalog staged on all four
nodes' local ext4 Docker storage and mounted read-only. Both sources reported
successful checks with zero drift and conflicts. The directory observer left
`/profile-cache` empty. The new Prometheus rules are tested but still require a
monitoring deployment to become active. Existing hunter SQLite storage remains
unchanged.
