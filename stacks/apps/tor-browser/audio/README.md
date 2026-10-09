# Kasm sidebar audio

This extension plays the container desktop's mixed output through Kasm's existing
MP2/MPEG-TS relay. Playback starts on a user click and closes on desktop disconnect.

## Layout

- `src/sidebar.js`: browser button and playback lifecycle; no build step.
- `install.py`: startup-time asset installation and HTML patching.
- `vendor/jsmpeg/`: untouched upstream decoder, license, and provenance note.
- `tests/integration/`: filesystem installer checks, installer CLI, decoder compatibility,
  browser/relay tests, and the Compose/startup installation contract.
- `tests/helpers/`: local HTTP/WebSocket relay used by browser tests.
- `tests/fixtures/`: authored Kasm sidebar shell and synthetic tone; no session data.

Python is used for installation because the deployed image has Python 3.10 but no
Node.js. Installation uses only the standard library. Node, pytest, Playwright,
Vitest, and ws are development dependencies, not container runtime requirements.

## Tests

From the repository root:

```sh
task test -- tor-browser
task test:integration -- tor-browser
```

All current tests exercise integration boundaries; there is no unit suite yet.
The repository runner discovers `pyproject.toml` and `package.json` independently.
For a direct run here, use `uv run pytest` and `npm ci && npm test`. The browser
suite installs its pinned Chromium build automatically; a clean Linux runner may
also need `npx playwright install --with-deps chromium` to provide system libraries.
Python installer coverage must reach 90%; coverage does not include vendored code.
PyYAML is a test-only dependency for reading the production Compose manifest.
Deployment tests reconstruct its config mounts in a temporary directory and run
the actual startup audio function against a fixture webroot. They also check that
the function is called before Kasm starts, failure is reported without blocking
the desktop, and the audio route retains its authentication and origin restriction.

The browser suite runs the real installer, serves its HTML and assets through a
local subprocess, and sends the synthetic MP2 tone over a real WebSocket. It checks
non-silent samples scheduled through real WebAudio, both HTML entry points, explicit
click-to-start, repeated toggles, desktop disconnect, rejected/closed connections,
timeout, browser suspension, and disconnect during a pending resume.

These tests do not run Traefik, Authentik, a real Kasm desktop, or physical speakers.
The sidebar HTML fixture covers the known DOM contract rather than guaranteeing
compatibility with future Kasm releases. WebAudio observation and the pending-resume
case instrument browser APIs; the latter still needs an owned seam to strictly
meet the repository's no-third-party-mocking guideline.

## Installation contract

The installer source directory must contain this layout, both locally and when
mounted through Docker configs:

```text
/opt/homelab-audio/
  install.py
  src/sidebar.js
  vendor/jsmpeg/jsmpeg.min.js
  vendor/jsmpeg/LICENSE
```

Run `python3 /opt/homelab-audio/install.py` before starting KasmVNC; an optional
positional argument selects a test webroot. The default is `/usr/share/kasmvnc/www`.
The installer updates `index.html` and `vnc.html`, preserves other scripts, and adds
content hashes to audio asset URLs. Startup should warn and continue if this
optional installation fails. Docker configs must be renamed when their contents
change. Compose mounts these files and `scripts/browser-prestart.sh` runs the
installer before starting Kasm. The audio and prestart config names use the first
12 characters of their source SHA-256; update both the definition and mount name
when the corresponding file changes.

The proxy must route same-origin `/kasm-audio` requests through Authentik to the
existing TLS relay on port 4901, with the browser's existing Kasm credentials.
Compose declares this route with an exact same-origin `Origin` header match and
explicit service assignments for both audio and desktop routers.
No credentials are embedded in the frontend. Audio connections are independent of
VNC server sessions: UI disconnect cleanup is not server-enforced revocation, and
Authentik logout should not be assumed to close an already-open stream.

After deployment, verify the sidebar, audible playback and lip sync through the
normal Tor URL. Do not treat local test success as proof of live proxy authentication
or server-side logout handling.
