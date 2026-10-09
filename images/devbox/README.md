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

When upgrading, update both the release archive URL and its checksum in the
Dockerfile. The build checks both `mcli --version` and `mc --version`. License
and attribution files are installed under `/usr/local/share/doc/mcli`.

Rebuild and redeploy the consuming stack to get the new client; this does not
change an already-running devbox or migrate an object-storage server.
