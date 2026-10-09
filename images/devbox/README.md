# Shared devbox image

This image is used by the code-server and claudecodeui stacks.

## S3 client

The image installs Silo's [mcli client](https://github.com/pgsty/mc), not the
Silo storage server. The Linux amd64 archive is pinned to
`RELEASE.2026-09-16T00-00-00Z` and verified against its SHA-256 checksum during
the build. This matches the existing amd64-only kubectl and yq downloads.

Use `mcli` for new commands. An `mc` symlink preserves the old command name;
the client continues to use `~/.mc` configuration and `MC_*` environment variables.
Upstream self-update is disabled; upgrade through an image rebuild instead.

When upgrading, update `MCLI_RELEASE`, `MCLI_VERSION`, and `MCLI_SHA256` at the
top of the Dockerfile. The build checks both `mcli --version` and `mc --version`. License
and attribution files are installed under `/usr/local/share/doc/mcli`.

Rebuild and redeploy the consuming stack to get the new client; this does not
change an already-running devbox or migrate an object-storage server.

## Package versions and validation

Edit version defaults at the top of `Dockerfile`, or pass a Docker build argument.
Arguments are consumed beside each install step so changing an agent version
preserves earlier build layers. Empty installer versions and npm `latest` values
remain floating; apt packages, fnm, Forge, and the R languageserver are also not
fully pinned. This is not a fully reproducible toolchain lockfile.

CloudCLI is pinned to `1.37.3`. Claude is pinned to `2.1.210`, the version verified
in the working code-server container and used to repair the broken CloudCLI
container. Verify Claude chat in CloudCLI before selecting a newer version.
Claude installs separately with optional dependencies enabled, and the build
runs `claude --version`, `codex --version`, and `cloudcli --version` as `coder`.
`DISABLE_AUTOUPDATER=1` disables Claude's background updater; upgrade through an
image rebuild. Manual npm installs can still modify a running container.

The observed failure was an incomplete npm installation with an existing
`.claude-code-*` staging directory. Whether it originated in a build or a later
runtime update is unconfirmed. The checks catch a missing launcher at build time;
they do not prove that an authenticated chat session works.

## Persistent configuration

Both stacks mount the same Claude directory and set
`CLAUDE_CONFIG_DIR=/home/coder/.claude`. This puts the global `.claude.json`
inside that volume, alongside credentials, settings, and project history.
The shared entrypoint runs as `coder` before either application starts. It:

- Copies a legacy `~/.claude.json` into the volume if no shared copy exists.
- Keeps an existing shared copy and saves differing legacy files as
  `.claude.json.pre-migration.*` with mode `0600`.
- Creates `~/.claude.json` as a compatibility symlink to the persisted file.
- Locks the migration across both containers and publishes the initial file
  atomically. Unexpected symlinks or non-file config paths fail startup with a
  diagnostic instead of replacing user data.

CloudCLI uses `DATABASE_PATH=/home/coder/.cloudcli/auth.db`, inside its existing
volume. Its preflight creates every bind source with UID/GID `1000`, including
Codex's directory, independently of a prior code-server deployment.

### Preserve existing state before the first rollout

A new container cannot recover files from the old container's writable layer.
Stop active Claude sessions in both applications, then migrate each current
container **before replacing it**. Run the following from this checkout on the
Swarm node that owns the container, substituting its actual ID:

```bash
devbox_container=<running-container-id>
docker cp images/devbox/devbox-entrypoint.sh "${devbox_container}:/tmp/devbox-entrypoint.sh"
docker exec --user 1000:1000 \
  --env CLAUDE_CONFIG_DIR=/home/coder/.claude \
  "${devbox_container}" bash /tmp/devbox-entrypoint.sh true
```

Run this for code-server and claudecodeui. Migrate the preferred configuration
first; the second container's differing configuration is preserved for manual
reconciliation. The helper requires `flock` (`util-linux`). Keep sessions stopped
until both applications have been replaced so older processes cannot rewrite the
legacy path during migration.

Check the current CloudCLI database location before replacement. If it still
uses a legacy location inside the npm package, take a consistent SQLite backup
and migrate it to the mounted `.cloudcli/auth.db` first. Do not overwrite an
existing database or copy a live SQLite main file without its pending journal
state. CloudCLI 1.37.3 normally already uses the mounted location.

### Build and rollout

The existing PR workflow builds affected devbox consumers without pushing an
image. It also runs the migration tests inside the Docker build. After merge,
the main build publishes `:latest` and the immutable commit-SHA tag. Release
promotion later adds a semantic-version tag.

After the main build succeeds, set `IMAGE_TAG` in `.env` to that build's commit
SHA and deploy both consumers together:

```bash
task deploy -- code-server claudecodeui
```

The compose fallback tags still refer to previously published releases; merging
this PR alone does not update those deployed images. Use the same new SHA for
both applications. Verify Claude chat, save a setting, replace the containers,
and verify that the setting and authentication persist.

### Local regression tests

```bash
python3 images/devbox/tests/test_entrypoint.py -v
```

The tests use temporary home directories and do not access real credentials.
