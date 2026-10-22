# FreeCAD

One FreeCAD desktop served to the browser through LinuxServer's Selkies image.
The service uses Traefik HTTPS and the existing `authentik@swarm` middleware.
Image version: `lscr.io/linuxserver/freecad:1.1.4-ls155`.

## Deploy

From the repository root:

```bash
task deploy:plan -- freecad
task deploy -- freecad
```

Open `https://freecad.${BASE_DOMAIN}/`, substituting your configured domain.
The stack declares Authentik and reverse-proxy as dependencies. Existing
`BASE_DOMAIN` and optional `TZ` settings are sufficient; no new application
password or environment variable is required.

The hostname must resolve to Traefik. If your Authentik proxy provider uses
per-application rules, add this hostname to the appropriate application/provider
and proxy outpost. A domain-wide provider can cover it through the existing
configuration. The stack attaches the middleware; it does not create Authentik
providers or change their access policies.

## Files and session

Save CAD projects in `/config/Projects` inside the desktop. Browser uploads and
downloads default to this directory. Settings and files under `/config` persist
at `/mnt/iscsi/app-data/freecad`; pre-flight creates both directories as 1000:1000.
Include that path in your backup coverage. Files saved elsewhere may not persist.

The service exposes one shared desktop, not an isolated workspace per Authentik
user. Keep it at one replica. Updates and rollbacks stop the previous instance
before starting the replacement; save open work before redeploying. Saved files
survive replacement, but the running session and unsaved edits do not.

The stack has no published host ports. Traefik routes both the UI and streaming
WebSockets to internal HTTP port 3000, with HTTPS on the browser connection.
It starts with CPU rendering and a 1 GiB `/dev/shm` tmpfs mount compatible with
Swarm. It can run on eligible nodes without a GPU label; `old` nodes are excluded
using the same placement convention as the devbox.

CAD models, project-specific scripts/macros, drawings, exports and parts lists
are personal application data. Keep them in persistent FreeCAD storage and its
backups, outside version control. Deployment provisions the desktop and empty
project directories; it does not install personal projects or macros.

## Deployment checks

```bash
docker service ps freecad_freecad
docker service logs --tail 100 freecad_freecad
```

After deploying, check that a signed-out browser goes through Authentik, the
desktop loads and accepts mouse/keyboard input, and a small test project can be
saved and reopened from `/config/Projects`. Verify persistence after a planned
service replacement once work is saved. If the page loads without a desktop,
check the streaming WebSocket in the browser network panel and the service logs.

Configuration validation can run without a Docker daemon. Runtime checks must
cover browser access through SSO, editing/saving/reopening a small project, and
saved-file persistence through a planned service replacement.

## Upstream references

- [FreeCAD image documentation](https://docs.linuxserver.io/images/docker-freecad/)
- [Pinned image release](https://github.com/linuxserver/docker-freecad/releases/tag/1.1.4-ls155)
- [Selkies reverse proxy setup](https://docs.linuxserver.io/selkies/user-guide/reverse-proxy/)
