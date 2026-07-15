# CHANGELOG

<!-- version list -->

## v3.23.1 (2026-07-15)

### Bug Fixes

- Unlock coder account so devbox sshd accepts pubkey auth
  ([`2e5002c`](https://github.com/chutch3/homelab/commit/2e5002c1abffe2e7e7e3d25faace62ae782ea0b5))


## v3.23.0 (2026-07-13)

### Bug Fixes

- Bumping the api version in budget mcp
  ([`f65168b`](https://github.com/chutch3/homelab/commit/f65168b04e0fee7cb88fafe07306b2fffa0b990e))

- Upgrade actual-mcp bundled api to 26.5.2 at startup to match server schema
  ([`36916f7`](https://github.com/chutch3/homelab/commit/36916f79e608db0c7120fbd9cb9c834cb4b6f26b))

### Chores

- Bump kenku
  ([`b13a5e6`](https://github.com/chutch3/homelab/commit/b13a5e616830c4dd81047c2de51ce0bda06961ea))

- Bump warden
  ([`491d628`](https://github.com/chutch3/homelab/commit/491d62812bb6af2c5706b7f4cc6d5935f0eb2e02))

### Features

- Comments and moved inprogress downloads off of network storage
  ([`def0b7b`](https://github.com/chutch3/homelab/commit/def0b7bc7247526eeb3e96a442c53542c7d79554))


## v3.22.2 (2026-06-30)

### Bug Fixes

- Paginate warden arr queue fetch to avoid truncating large queues
  ([`8a4ddcd`](https://github.com/chutch3/homelab/commit/8a4ddcda045755a42e0e5d2e2f640d251ea9eca2))


## v3.22.1 (2026-06-29)

### Bug Fixes

- Stop warden flagging queued and slow downloads as stale
  ([`a9e2b57`](https://github.com/chutch3/homelab/commit/a9e2b57babd230d9eeffb7a94e2c55e95a302af2))


## v3.22.0 (2026-06-25)

### Bug Fixes

- Bump takeout-manager and takeout-worker to 3.21.0
  ([`f319a57`](https://github.com/chutch3/homelab/commit/f319a57ff3b718b9bf5c4b820f385e0f06d36873))

- Move forgejo SSH to port 2223 to avoid conflict with traefik ssh entrypoint
  ([`9863762`](https://github.com/chutch3/homelab/commit/986376287e8e8add2b6734bdd822459b979f0ab2))

- Run takeout-manager and worker via uv run to activate venv
  ([`9e1dc7d`](https://github.com/chutch3/homelab/commit/9e1dc7d479c18f3642e792d0bb73eacee0935290))

### Chores

- Bump kenku
  ([`98e5cd0`](https://github.com/chutch3/homelab/commit/98e5cd015bcb801c2d19e6f82cdd15cffa605f31))

- Bump takeout-manager and takeout-worker default to 3.22.0
  ([`f7ae5db`](https://github.com/chutch3/homelab/commit/f7ae5dbe27ca6a48c08f7fc82ae9f21ae81af101))

- Retire kenku-pg-backup sidecar now that fiber backs up kenku
  ([`636c169`](https://github.com/chutch3/homelab/commit/636c169dd123ebe3f3186eafb3c37f8c99fe95c3))

- Set excalidraw fiber schedule to nightly
  ([`9cf07d0`](https://github.com/chutch3/homelab/commit/9cf07d0b941be2a43bbf805e46464b2f6b7b0c18))

### Documentation

- Document fiber bowl daily kopia policy and pgdata exclusions
  ([`9af889d`](https://github.com/chutch3/homelab/commit/9af889d8ac78eb362cc18879a48fd422d8325811))

### Features

- Prune orphaned services on stack deploy by default (configurable via -e prune)
  ([`9395c43`](https://github.com/chutch3/homelab/commit/9395c430032cc3aea325519ec5315110646d4710))

- Wire batch-1 dbs (downloads, prefect, forgejo, librechat) into fiber discovery
  ([`40b146f`](https://github.com/chutch3/homelab/commit/40b146f0e821f8bcf205880628baea51c4df091a))

- Wire excalidraw postgres into fiber discovery (m3 prove-one)
  ([`cbeb085`](https://github.com/chutch3/homelab/commit/cbeb085a0715887a483de49e36f967baa92d55a7))

- Wire immich and authentik into fiber discovery (batch-2)
  ([`55cc669`](https://github.com/chutch3/homelab/commit/55cc66933e22825d673dceb7d50ead6f1aacba2d))


## v3.21.0 (2026-06-23)

### Bug Fixes

- Promote images from :latest so unchanged images get the release version
  ([#90](https://github.com/chutch3/homelab/pull/90),
  [`7135ad9`](https://github.com/chutch3/homelab/commit/7135ad9a31568fec4580eaf27d6e150cc151fe77))

### Chores

- Bump kenku to 0.33.1 and sync uv.lock version ([#89](https://github.com/chutch3/homelab/pull/89),
  [`805b84f`](https://github.com/chutch3/homelab/commit/805b84ffbe9f7da243e8155e0c4f4cf7876ac187))

- Bump kenku to 0.33.1 in downloads stack ([#89](https://github.com/chutch3/homelab/pull/89),
  [`805b84f`](https://github.com/chutch3/homelab/commit/805b84ffbe9f7da243e8155e0c4f4cf7876ac187))

- Bump takeout to python 3.12
  ([`b8771eb`](https://github.com/chutch3/homelab/commit/b8771ebf1966b33265f4c557910ddaf0e8ca8ce4))

- Sync uv.lock to released homelab version 3.20.0
  ([#89](https://github.com/chutch3/homelab/pull/89),
  [`805b84f`](https://github.com/chutch3/homelab/commit/805b84ffbe9f7da243e8155e0c4f4cf7876ac187))

### Continuous Integration

- Nightly/on-demand e2e workflow
  ([`ade7bd4`](https://github.com/chutch3/homelab/commit/ade7bd45407d6fbaafbe2959f7a138f51b1b424b))

### Features

- Local ghcr prune task (ci gc + task ghcr:prune)
  ([`e341016`](https://github.com/chutch3/homelab/commit/e3410169c14c9875c051cf296d1429d9f0e8c8b2))

- Pin custom images to a deploy version via IMAGE_TAG default
  ([#91](https://github.com/chutch3/homelab/pull/91),
  [`35ab0ad`](https://github.com/chutch3/homelab/commit/35ab0add090950ac3d244263fd3aeb8f576fa6ca))

### Refactoring

- Gate coverage on combined unit+integration
  ([`faf2e10`](https://github.com/chutch3/homelab/commit/faf2e10ce4e4db2d3040c940faff9f4e97f389d8))

- Retire scripts/ in favor of lib/ and tools/ ([#87](https://github.com/chutch3/homelab/pull/87),
  [`751ea17`](https://github.com/chutch3/homelab/commit/751ea177e957519ca2168eaec1dc401b75ec73c8))

### Testing

- Raise custom-exporter coverage to 90 (entrypoint, run_server, runner error path)
  ([#84](https://github.com/chutch3/homelab/pull/84),
  [`8ea49a4`](https://github.com/chutch3/homelab/commit/8ea49a41cd4993ed5d44023725999bec9c326742))

- Raise takeout-manager coverage gate to 90 ([#86](https://github.com/chutch3/homelab/pull/86),
  [`49fe5e8`](https://github.com/chutch3/homelab/commit/49fe5e87c0c4db97fd7f7e5ebc9bc9272a13ce36))

- Raise takeout-worker coverage to 90 (runners, logger, extract error paths)
  ([#85](https://github.com/chutch3/homelab/pull/85),
  [`c368a59`](https://github.com/chutch3/homelab/commit/c368a5957103595ead92ef8250304e0380c8e8fd))

- Vendor bats helpers instead of git submodules ([#88](https://github.com/chutch3/homelab/pull/88),
  [`d31ef27`](https://github.com/chutch3/homelab/commit/d31ef27c8bb46615cf387cb912af271b05e3a710))


## v3.20.0 (2026-06-23)

### Bug Fixes

- Retag sha via imagetools instead of comma tags in bake
  ([`b566d1e`](https://github.com/chutch3/homelab/commit/b566d1e95a36c7103c82245bb62ccde30c2d69d1))

### Chores

- Remove monorepo build/release planning doc
  ([`e6f18c8`](https://github.com/chutch3/homelab/commit/e6f18c84bd5ea18c80b5b14cfe651859fa46dd94))

### Features

- Build and test only changed apps with per-image CI
  ([`ec72a4c`](https://github.com/chutch3/homelab/commit/ec72a4c43f0336f7d10ba5adf885858238f29979))

- Per-app release flow via tag promote and pin PR
  ([`affd6ec`](https://github.com/chutch3/homelab/commit/affd6ec637ffa3f6375cd879ab7a0df907c09b6b))

- Promote images on semantic-release; remove per-app release flow
  ([`79ac624`](https://github.com/chutch3/homelab/commit/79ac624f7becc3f2c6e9a3d85b70f35edf8882f3))

### Refactoring

- App-release promote-only (drop auto pin PR)
  ([`cf5314d`](https://github.com/chutch3/homelab/commit/cf5314de6226c204f8107bfd58b343b1ea2e03c3))


## v3.19.0 (2026-06-22)

### Bug Fixes

- Bail the sweep only on download-client outages, not stuck-count
  ([`10b2537`](https://github.com/chutch3/homelab/commit/10b2537d09965450aa9a07bc7dd770b8e642c57f))

- Bind indexer budget to the most-constrained indexer not the most-generous
  ([`b7f52fe`](https://github.com/chutch3/homelab/commit/b7f52fe1010c10a174201b0d482b488370114281))

- Keep poll cadence when quota-blocked so the queue janitor keeps running
  ([`8a94b85`](https://github.com/chutch3/homelab/commit/8a94b85dcabdc0955414711f1144cdea637ddd6b))

- Moved the HA MCP disabled tools to .env
  ([`d3dc81b`](https://github.com/chutch3/homelab/commit/d3dc81b074d1797f6b1204f07ffbbfb0a5a00c50))

- Place ollama via llm label instead of hardcoded hostname
  ([`fd62a88`](https://github.com/chutch3/homelab/commit/fd62a88127419e412ce59bdf1e3c8916e4a3cbbb))

- Rename librechat ollama endpoint off reserved name
  ([`72afdb7`](https://github.com/chutch3/homelab/commit/72afdb7d4b111f2d4ce54d6a7673b1e5679f2ba0))

### Chores

- Bump devbox version
  ([`25f38df`](https://github.com/chutch3/homelab/commit/25f38dff00028e82540ad102ea26e9c5e65c3820))

- Bumped kenku
  ([`35a9842`](https://github.com/chutch3/homelab/commit/35a984278ce0f33292ebff0ddd8903a4c7019965))

- Disable ha-mcp search mode and prune to a lean tool set
  ([`f8cc253`](https://github.com/chutch3/homelab/commit/f8cc253c69ac07fe95302c0a28ac914fadd4db76))

- Move ollama to the rtx 3090
  ([`40313ab`](https://github.com/chutch3/homelab/commit/40313ab6327300cd2933db11a8d8b9ae5cf993e3))

### Documentation

- Add warden readme with tick-flow diagram
  ([`9957546`](https://github.com/chutch3/homelab/commit/99575461c78083513fd4cdf597bb3d52b4dd6d86))

- Capture local-model mcp findings for librechat
  ([`6e22e92`](https://github.com/chutch3/homelab/commit/6e22e9243c2c3aa91d6edc8c75e01725fc338198))

- Document declarative pre-flight provisioning; fix tor-browser README
  ([`758229b`](https://github.com/chutch3/homelab/commit/758229b5136374c5d2179c7c2ec2d126a7227f81))

### Features

- Add declarative directories provisioning to preflight role
  ([`ae53cba`](https://github.com/chutch3/homelab/commit/ae53cba514cffe53629893f8fd3579aeb8930220))

- Add fiber container-discovery provider + unprivileged compose e2e
  ([#74](https://github.com/chutch3/homelab/pull/74),
  [`85d5e9b`](https://github.com/chutch3/homelab/commit/85d5e9bcb98235780d10106a70bf72ab14f6365c))

- Add fiber db dump manager
  ([`4cee1b6`](https://github.com/chutch3/homelab/commit/4cee1b69b31f768c9ff015dcb2a8cfdbe04955eb))

- Add files and templates provisioning to preflight role
  ([`86ac9c2`](https://github.com/chutch3/homelab/commit/86ac9c20de49e79a27cfb599f4f94f017aedeaee))

- Add never-searched backlog panel
  ([`59a2374`](https://github.com/chutch3/homelab/commit/59a2374667f1f4bc6fc883fc78cc2094767a2053))

- Add no-progress panel and document no-progress env
  ([`3cb2cf4`](https://github.com/chutch3/homelab/commit/3cb2cf4b2e4ffa6d48093ef7817d16f772d42a3f))

- Add open-webui stack for local-model mcp tools
  ([`cfa30a4`](https://github.com/chutch3/homelab/commit/cfa30a4b62fad1bf86483816f7c8197d562740e0))

- Add pure no-progress tracker
  ([`c2a7a71`](https://github.com/chutch3/homelab/commit/c2a7a71e5a51e2ea2431372c434fd72ffc416495))

- Add queue list and remove to the arr client
  ([`8ecc711`](https://github.com/chutch3/homelab/commit/8ecc7119ff497f4990bc07d4871f1459d305dbac))

- Add queue sweeper policy with mass-unhealthy guard
  ([`0dc33a0`](https://github.com/chutch3/homelab/commit/0dc33a0aff926041a855fa9fe763ecfb5993e878))

- Add QueueItem model and stale-download detector
  ([`6ac59b3`](https://github.com/chutch3/homelab/commit/6ac59b3493c3e0e2bbedd9479ef997faa3710d0a))

- Add stale-sweep panels and document sweep env
  ([`bb5df7a`](https://github.com/chutch3/homelab/commit/bb5df7a4a2eff3682295fb039e6b981dfcde1474))

- Add warden quota-aware *arr hunter
  ([`d6ab427`](https://github.com/chutch3/homelab/commit/d6ab427fe1cf725623390b877f9e2f0f04382294))

- Back off repeatedly-unfindable items and hunt the full missing backlog
  ([`861b8ea`](https://github.com/chutch3/homelab/commit/861b8eaea2000ebf3430d01891dce5b360c9feb6))

- Expose never-searched backlog gauge
  ([`45b7920`](https://github.com/chutch3/homelab/commit/45b7920326761b8a56f645a71cfbfad71f8f21ee))

- Hunt least-recently-searched missing items first
  ([`070cfbe`](https://github.com/chutch3/homelab/commit/070cfbe48ca7283016bc239f7cf81bb9475e25d4))

- Log per-title search triggers and idle hunt ticks
  ([`2b2119e`](https://github.com/chutch3/homelab/commit/2b2119e01014e145c569ba31619feb1a36417b21))

- Parse downloadId and sizeleft into QueueItem
  ([`5c85b31`](https://github.com/chutch3/homelab/commit/5c85b31772d1dad7c0723bd36dbd6aa54c0f6874))

- Persist no-progress anchors in a queue-progress repository
  ([`5e41872`](https://github.com/chutch3/homelab/commit/5e418720569dfafde9aa91e2c77fc1ce24168678))

- Read *arr lastSearchTime into WantedItem
  ([`7003e79`](https://github.com/chutch3/homelab/commit/7003e7989064fbd0327a53835d2880005bed32d8))

- Remove no-progress downloads each tick via tracker + persisted anchors
  ([`7273973`](https://github.com/chutch3/homelab/commit/72739739fc43781da4de0fad692bd7e77b5b5e4c))

- Share devbox workspace and ssh keys with rstudio
  ([`cd12974`](https://github.com/chutch3/homelab/commit/cd12974f123b0261756d2f7f82ee31cd9b2b837f))

- Support cache mount in preflight directories; migrate librenms
  ([`80c57eb`](https://github.com/chutch3/homelab/commit/80c57eb28ded2d23f81ae629b1116191936d1312))

- Sweep stale downloads and exclude queued items each tick
  ([`99a1b81`](https://github.com/chutch3/homelab/commit/99a1b81092e5b4ab0673b9791b8771b9a5ffe2d8))

- Track grab efficacy as hit/miss rate per source and indexer
  ([`112cd5b`](https://github.com/chutch3/homelab/commit/112cd5b551e30270719d901c6e0f0b06a92787a6))

### Refactoring

- Align files with secrets from_file convention, reuse mount vars, dedup, dynamic ssh key
  ([`b17a7aa`](https://github.com/chutch3/homelab/commit/b17a7aad680684bf4e0b44bea8b87271f68c136a))

- Consolidate fiber e2e suite under app/tests ([#75](https://github.com/chutch3/homelab/pull/75),
  [`7bc1120`](https://github.com/chutch3/homelab/commit/7bc1120316ef2ba9c867c454ba2d75d87e966863))

- Dedupe arr timestamp parsing and tidy lrs tests
  ([`c7850d7`](https://github.com/chutch3/homelab/commit/c7850d7f05305f307b0abd831ba2cf0b4f6a8906))

- Extract quota-state publishing and unify the arr test double
  ([`99eda27`](https://github.com/chutch3/homelab/commit/99eda2784e00e4e580fa3fed035656a3d943e63e))

- Migrate code-server provisioning to preflight directories/files/templates
  ([`3b7a937`](https://github.com/chutch3/homelab/commit/3b7a937842ae95efe648f1605a4053f8332db6de))

- Migrate tor-browser provisioning to preflight directories
  ([`721118e`](https://github.com/chutch3/homelab/commit/721118e1f854c52d5a1c4d18c0b2c68163f0c293))

### Testing

- Add real-subprocess integration harness with pytest-httpserver
  ([`6e2a45c`](https://github.com/chutch3/homelab/commit/6e2a45ca985a05eba8abacca3a8aa5e4e7df513a))

- Cover hunt, quota, provenance and degradation end-to-end
  ([`a613202`](https://github.com/chutch3/homelab/commit/a6132026b8de79b9be30232c77d560757d388dba))

- Cover least-recently-searched ordering end-to-end
  ([`52b3a00`](https://github.com/chutch3/homelab/commit/52b3a00c4836dc999f6e0cc22ad342ac442f67f4))

- Cover most-constrained-indexer budget through the subprocess harness
  ([`490ddaa`](https://github.com/chutch3/homelab/commit/490ddaac0b0bba6d4150d81fa456451a392603a2))

- Cover no-progress removal end-to-end
  ([`4810caf`](https://github.com/chutch3/homelab/commit/4810caf3152dea4f50e16e3d9c87567b85f8e5f6))

- Cover stale sweep and hunt-exclusion end-to-end
  ([`4b6fe99`](https://github.com/chutch3/homelab/commit/4b6fe9964f76992fc871be2fbfbd9e2a82aa2d51))

- Cover sweep bail, removal failure and blocked-source sweep
  ([`acd0061`](https://github.com/chutch3/homelab/commit/acd0061107edd4ba07bea6d277d9614c8983ad24))

- Dedupe progress-repo helper and cover false-positive safety e2e
  ([`d3bfd64`](https://github.com/chutch3/homelab/commit/d3bfd64a4dcbe0ad87221dbd322100f9d431b97d))

- Gate integration suite and align coverage semantics with fiber
  ([`d1b85a4`](https://github.com/chutch3/homelab/commit/d1b85a43056ff79bb1120ff573bd03ff30665378))

- Relocate in-process tests into the unit tier matching fiber layout
  ([`4b7ebe5`](https://github.com/chutch3/homelab/commit/4b7ebe571b2c27dfe1162185ce896d3ed5fe9d4b))


## v3.18.0 (2026-06-15)

### Bug Fixes

- Bump librechat config to v9 to drop internal ip from allowedaddresses
  ([`3a95d04`](https://github.com/chutch3/homelab/commit/3a95d04ca208fa05fdc0a5b59694d93245e2fb25))

- Disable chromium sandbox for mermaid renderer
  ([`b4f645c`](https://github.com/chutch3/homelab/commit/b4f645ceb39c714f60302f531aa2c25e8f4c7dcc))

- Raise ollama default context length to 16384 for mcp tool schemas
  ([`d3b9753`](https://github.com/chutch3/homelab/commit/d3b975358cd616e4dd0d74ffc09c1382153e18bd))

- Set USER and LOGNAME env vars in devbox code-server sessions
  ([`f103f1d`](https://github.com/chutch3/homelab/commit/f103f1d0a977250967eff15d54401d6b4c49f3b4))

- Switch published ssh port for the code server stack
  ([`79f764b`](https://github.com/chutch3/homelab/commit/79f764b3d1f7a98e778180486b5fc7002d1e6ca6))

### Chores

- Bump kenku to 0.13.1 in downloads stack
  ([`a462f13`](https://github.com/chutch3/homelab/commit/a462f13254e269f6b0a12ab5e7f26b97f8b82f42))

- Bump kenku to 0.13.2 in downloads stack
  ([`e9d5edd`](https://github.com/chutch3/homelab/commit/e9d5eddf9cad356317585c1c348c8a9650a7deb9))

- Bump kenku to 0.14.0 in downloads stack
  ([`3f87656`](https://github.com/chutch3/homelab/commit/3f87656dcaa5a31e782e5f9efd4d3c04d28aff36))

- Bump kenku to 0.24.0 in downloads stack
  ([`34f85e2`](https://github.com/chutch3/homelab/commit/34f85e23f61ef69401fb8acadefa060397a111e4))

- Pin claudecodeui devbox image to sha256 digest
  ([`37b82ba`](https://github.com/chutch3/homelab/commit/37b82bac7591a128fdc65cbe257ea76e95bc0264))

- **kenku**: Bump chapter-sync interval to 24h
  ([`9ece3de`](https://github.com/chutch3/homelab/commit/9ece3dea4f42b12cecedcbe59a2afa213a81bdbe))

- **kenku**: Pin 0.25.1 (per-series chapter ids, sync save-failure surfacing)
  ([`6506f76`](https://github.com/chutch3/homelab/commit/6506f765f8376d778b759c41e892a75a37fc3423))

### Features

- Add home assistant mcp servers to librechat
  ([`0efc5d9`](https://github.com/chutch3/homelab/commit/0efc5d97866958bdb2a6bc86805fcf3ae6309501))

- Add mermaid live editor stack
  ([`bee8d7c`](https://github.com/chutch3/homelab/commit/bee8d7c1273d1e79b49df6a3ae14e69f9087826f))

- Bump kenku
  ([`d5abb96`](https://github.com/chutch3/homelab/commit/d5abb967e23aa952896703ca58606d7651da4635))

- Bump kenku version
  ([`6adf013`](https://github.com/chutch3/homelab/commit/6adf013dff72f3a639132e01409b4f17ffdbadc2))

- Configure act_runner labels via config file and pin to 0.6.1
  ([`3904520`](https://github.com/chutch3/homelab/commit/39045203cdc1bc880069d059efe996da2aa2199e))

- Updated devbox and pinned it to a sha
  ([`d698c4f`](https://github.com/chutch3/homelab/commit/d698c4f9e27d9e063863c645216fae41d72374dc))


## v3.17.0 (2026-06-08)

### Bug Fixes

- Add GIT_AUTHOR_NAME and GIT_AUTHOR_EMAIL to code-server pre-flight
  ([`3b2d471`](https://github.com/chutch3/homelab/commit/3b2d471ebf950f35268ab90a36483d96159d88a7))

- Bump authentik to 2026.5.2 and expand proxy outpost /dev/shm to 512MB
  ([`c0250ea`](https://github.com/chutch3/homelab/commit/c0250ea4b719964f9ba5b24064e92037e89b5bcc))

- Increase actual-budget MCP timeout to 300s
  ([`f37264c`](https://github.com/chutch3/homelab/commit/f37264c45e8f529051446f896ab6b2062f17d257))

- Propagate bitwarden session via block-level environment
  ([`a5a5407`](https://github.com/chutch3/homelab/commit/a5a5407c25757cab78c7362bc33221733cb86c5a))

### Chores

- Bump kenku to 0.12.0 in downloads stack
  ([`61d90b1`](https://github.com/chutch3/homelab/commit/61d90b1a2a6b29db38423ed1a01ade660dd19d43))

- Untrack devbox spec from repo
  ([`a94b329`](https://github.com/chutch3/homelab/commit/a94b329720fdd345872c61d00d680907da2bdba0))

### Continuous Integration

- Run preflight unit hook only on relevant changes and stop lockfile churn
  ([`4dd3260`](https://github.com/chutch3/homelab/commit/4dd3260bda53fa8b7939d314e24293ff93334a0b))

### Documentation

- Add devbox SSH and dev environment design spec
  ([`7352c4a`](https://github.com/chutch3/homelab/commit/7352c4a28b4c3a9a14d6b75b445864e5a8747ac9))

### Features

- Add SSH access, supervisord, R, and mc to devbox
  ([`c4f3b22`](https://github.com/chutch3/homelab/commit/c4f3b22e95fad39550a464a7ab30e6c34db8b3fa))

- Replace tranga with kenku as manga downloader
  ([`d4ab15b`](https://github.com/chutch3/homelab/commit/d4ab15bb7805daf6e5fbb3701cc849a1ecada472))


## Unreleased

### Bug Fixes

- Bump authentik images from 2024.12.5 to 2026.5.2

## v3.16.0 (2026-06-01)

### Bug Fixes

- Abort reboot playbook if OCFS2 unmount fails
  ([`4a50c81`](https://github.com/chutch3/homelab/commit/4a50c81b3cc308b7062456a530dbb471422966e7))

- Add dnsrr endpoint mode to immich-postgres
  ([`8024ed4`](https://github.com/chutch3/homelab/commit/8024ed4c263458cddef04bbb8d203699d2ea9f19))

- Add NVIDIA driver capabilities and remove generic resource constraint from GPU services
  ([`f9e1bd8`](https://github.com/chutch3/homelab/commit/f9e1bd8fdcf565b283413fdb36968e27afa53a9c))

- Add step-by-step verification to OCFS2 unmount sequence
  ([`0219226`](https://github.com/chutch3/homelab/commit/0219226c479f9bd525f4cad278e1fbcab9142e72))

- Add sudo to omv-rpc and omv-salt calls in cert install script
  ([`1b14dea`](https://github.com/chutch3/homelab/commit/1b14deac17413001c6f65e849015578b850cd52d))

- Add typescript and remove dead fnm root chmod in devbox
  ([`0c82bc6`](https://github.com/chutch3/homelab/commit/0c82bc641f7e0457d660d27bc6e08a2b2c5f07b1))

- Convert cert-sync-nas scripts to docker configs for swarm node portability
  ([`981c672`](https://github.com/chutch3/homelab/commit/981c672c3bc6cd471b32447552e6eadd86f5a0bc))

- Correct OCFS2 unmount sequence to prevent journal corruption on reboot
  ([`fb05f0b`](https://github.com/chutch3/homelab/commit/fb05f0b707830fa39838844a50f98384a0bc6a1e))

- Patch actual-mcp migration check and bump actual-server to 26.5.2
  ([`4b116ac`](https://github.com/chutch3/homelab/commit/4b116acd6090223aa5f9f76c5606a877fdd057e4))

- Poll for docker shutdown instead of fixed pause before OCFS2 unmount
  ([`4a87fc4`](https://github.com/chutch3/homelab/commit/4a87fc43048d4d5b89a6dde28059fa3bf50126fe))

- Poll for iSCSI session termination after logout
  ([`faa0d61`](https://github.com/chutch3/homelab/commit/faa0d6199c1b0b77443ec08cae37897639617e3e))

- Remove false empty-directory check — mountpoint -q is sufficient
  ([`e725dcd`](https://github.com/chutch3/homelab/commit/e725dcddc655bca518e31523469cd3dd4506160c))

- Remove profilarr backup sidecar replaced by kopia
  ([`5cc2b6c`](https://github.com/chutch3/homelab/commit/5cc2b6c58b85f4c0a81e7131f0eda24bad410332))

- Replace blocking O2CB cluster-offline check with informational log
  ([`17f2400`](https://github.com/chutch3/homelab/commit/17f24008deaceac948055d7a4a5365b4b1eaf27b))

- Replace broken nordvpn credential variable indirection with direct env vars
  ([`2d5bf36`](https://github.com/chutch3/homelab/commit/2d5bf3659bc503bd9c3f1e51af55a67971c51a72))

- Replace community.docker SDK network module with CLI command
  ([`6048bea`](https://github.com/chutch3/homelab/commit/6048bea251f89bf4a01c280743a9ed4c53e1e886))

- Replace deprecated ansible fact vars and O2CB failed_when with retry loop
  ([`be09e89`](https://github.com/chutch3/homelab/commit/be09e89c624ae99c09a76aa5c2ecae8b000b0924))

- Resolve load-env path when swarm role is invoked via import_playbook
  ([`a7c69fd`](https://github.com/chutch3/homelab/commit/a7c69fd464772d2787aa38087a0a2f0c3b196656))

- Restore bookmarks.yaml with valid empty state
  ([`b613eb0`](https://github.com/chutch3/homelab/commit/b613eb0abf11c89dab60b012d053f51f1725d80b))

- Simplify fnm path setup in devbox and claudecodeui
  ([`cc0cc85`](https://github.com/chutch3/homelab/commit/cc0cc859827221dfa091ba48a26eba026cd330af))

- Use dnsrr for immich and sonarr, move Technitium query logs off iSCSI
  ([`7802546`](https://github.com/chutch3/homelab/commit/7802546ee03e82f05f82921f8985cd1292315920))

- Use full path for omv-rpc and omv-salt in cert install script
  ([`f823171`](https://github.com/chutch3/homelab/commit/f82317180e3cd3fe971b13b23f21a51075ab0000))

- Use mountpoint -q and sync after unmount to prevent premature fuser execution
  ([`f2ac1cb`](https://github.com/chutch3/homelab/commit/f2ac1cbb4608cc97e3bf2cbb81e977254f6e89fc))

- Use o2cb list-clusters to read cluster name instead of parsing cluster.conf
  ([`260a154`](https://github.com/chutch3/homelab/commit/260a1542c4821010587b76d94b81062fea9a1d6c))

### Chores

- Bump homelab version in uv lock
  ([`b07121d`](https://github.com/chutch3/homelab/commit/b07121dd120e473c83e55d14878e0b5017d5f333))

### Documentation

- Update code-server and tor-browser readmes to reflect automated pre-flight
  ([`86f758f`](https://github.com/chutch3/homelab/commit/86f758f8689a5ba143e85470026e327cc0f6c3b7))

- Update code-server README to document SSH_EXTRA_HOSTS variable
  ([`5849425`](https://github.com/chutch3/homelab/commit/584942521f07a5eddaca35653122500c78738919))

### Features

- Add homelab-health dashboard and status pipeline alert rules
  ([`9d6e010`](https://github.com/chutch3/homelab/commit/9d6e010920f0821006a7ee7277a75602cf01022e))

- Add preflight role for automated stack deployment prerequisites
  ([`446746d`](https://github.com/chutch3/homelab/commit/446746da00e19b7d16d5d9a03cce8546131c1a0f))

- Add secrets compare command to diff local vs Bitwarden with masked values
  ([`e27862c`](https://github.com/chutch3/homelab/commit/e27862ce64da6e68dcd1545df9e91824cd671262))

- Add setup.sh and update getting started docs
  ([`59b6c7d`](https://github.com/chutch3/homelab/commit/59b6c7d1f1c25fcb388325c32416550f93c8a4ad))

- Add status pipeline to publish Uptime Kuma data via Tailscale Funnel
  ([`c46f1d3`](https://github.com/chutch3/homelab/commit/c46f1d3008c91b3071d4f86dab451ff1ba835428))

- Add task-master-ai to devbox npm globals
  ([`8666ac9`](https://github.com/chutch3/homelab/commit/8666ac9c9f3c5d7ee7c01671432e770a5035bee9))

- Add VPN rotation, WireGuard keepalive, and gluetun auth for tor-browser
  ([`5840a5a`](https://github.com/chutch3/homelab/commit/5840a5a147497893c0d00b66d5255077127f14f3))

- Convert monitoring configs to swarm and enable minio metrics scraping
  ([`fba87ba`](https://github.com/chutch3/homelab/commit/fba87babc9c5cdc91c17eca7584a8c765987ec17))

- Refine grafana dashboards with cross-links node variable and gossip events panel
  ([`d4df524`](https://github.com/chutch3/homelab/commit/d4df52415c31a6099016721c5c9005c06b639c57))

- Replace manual setup scripts with hooks.sh lifecycle interface per stack
  ([`0439cc0`](https://github.com/chutch3/homelab/commit/0439cc03e9b681a3ff2bc3304ec661a59aebb790))

### Refactoring

- Inline librechat env vars from .env file
  ([`8b54b80`](https://github.com/chutch3/homelab/commit/8b54b806257d29372b04fc830f9c76c89322b87a))


## v3.15.0 (2026-05-25)

### Bug Fixes

- Add traefik.swarm.network label to all Traefik-exposed stacks
  ([`2c4e8fd`](https://github.com/chutch3/homelab/commit/2c4e8fd4e4db4f5d0e7e6ef91a83a76ad53cd174))

- Bump authentik images from 2024.12.3 to 2024.12.5
  ([`718ffa2`](https://github.com/chutch3/homelab/commit/718ffa25d836e195428ffec1dd185d29334b3f9a))

- Cast boolean variables with | bool filter in ops playbooks
  ([`9b86982`](https://github.com/chutch3/homelab/commit/9b86982a87a346fc08a1631793aa1350a73946e6))

- Convert librenms environment blocks to list format
  ([`1ef76d6`](https://github.com/chutch3/homelab/commit/1ef76d6fa4ffff3706fe763b1226eb6e231a3ba8))

- Correct invalid task commands and standardize to deploy:service/teardown:service
  ([`edbab6b`](https://github.com/chutch3/homelab/commit/edbab6bde09c09ab0b507611aa7c24e17a6ddd84))

- Ensure claude-code binary is executable after npm install
  ([`7923176`](https://github.com/chutch3/homelab/commit/79231763324c11f6c6751e6d7b9129529111fe87))

- Migrate dns volume to iscsi, disable ipv6, bump to 15.2.0
  ([`a5a21ee`](https://github.com/chutch3/homelab/commit/a5a21ee07f77dece28eca562b3d4e9873f2b1782))

- Simplify secrets login and harden bitwarden session handling
  ([`801f9c2`](https://github.com/chutch3/homelab/commit/801f9c236705f4084ca318322751d8efa111da63))

### Documentation

- Complete refactor of the documentation
  ([`cee0570`](https://github.com/chutch3/homelab/commit/cee05709d4bdbaac1277e5be6c53b806cba6a4f4))

### Features

- Add draw.io and LibreNMS application stacks
  ([`9e1ff2c`](https://github.com/chutch3/homelab/commit/9e1ff2c48ef9f6b59979e1da808dc9f764ecc2e3))

- Add GoatCounter analytics and LLM context files (llms.txt, AGENTS.md)
  ([`f8c66da`](https://github.com/chutch3/homelab/commit/f8c66dac59155ffc93e52f9f5398468da0a7a72a))

- Add setup scripts for draw.io and LibreNMS stacks
  ([`283248c`](https://github.com/chutch3/homelab/commit/283248c363fcd278b5c3a769570cd74df8e7ae18))

- Add snmp role with package-driven enable and snmp:configure tasks
  ([`a783b0a`](https://github.com/chutch3/homelab/commit/a783b0a323a1bf363dc5f9decce7a298776d9836))

- Add snmp.yml to secret sync and wipe
  ([`19189d5`](https://github.com/chutch3/homelab/commit/19189d54920e7a26348b1d66aaa9e7022d95c656))

- Add syslogng, snmptrapd sidecars and fix librenms compose configuration
  ([`bc205c4`](https://github.com/chutch3/homelab/commit/bc205c45dadf1a6e7e0266ad25c14705514802fe))

- Added kasmvnc based tor browser app with vpn and kill switch
  ([`8ff7e47`](https://github.com/chutch3/homelab/commit/8ff7e472c5e807e95c8f18545dbe006023335a1a))


## v3.14.0 (2026-05-18)

### Bug Fixes

- Add openssh-client so docker ssh contexts work
  ([`61e1d84`](https://github.com/chutch3/homelab/commit/61e1d840cd9e762ed34b6037982de321a45a21a8))

- Add tls labels to excalidraw-room and health path to storage monitor
  ([`5893b7a`](https://github.com/chutch3/homelab/commit/5893b7a781b3b98cb244c8b880f4ebebcc47a70e))

- Avoid bool filter on 'auto' string to suppress deprecation warning
  ([`f1e4c46`](https://github.com/chutch3/homelab/commit/f1e4c46c76213e0a83f76d63194f347ccb3d5066))

- Code-server now accessible via domain
  ([`28a29cb`](https://github.com/chutch3/homelab/commit/28a29cb4181b5284f80e39bb05887cc59bba99d1))

- Correct truncated panels array in cluster-health dashboard
  ([`f796029`](https://github.com/chutch3/homelab/commit/f79602923a4334eab3ce455caf0bdf245ee8eee7))

- Correct workspace volume mount path in devbox services
  ([`5e6412d`](https://github.com/chutch3/homelab/commit/5e6412d56710da7bea9693bd288a3ac51b18a5fb))

- Delegate compose file stat checks to localhost
  ([`9559f53`](https://github.com/chutch3/homelab/commit/9559f53e903f48d06c905d7adbc68498fcec287c))

- Delegate docker stack operations to localhost to use uv environment
  ([`336ba13`](https://github.com/chutch3/homelab/commit/336ba130b202d5e90597b100583c20e4ec237e43))

- Delegate secrets push/pull file operations to localhost
  ([`ea0aa34`](https://github.com/chutch3/homelab/commit/ea0aa345ad2f240f79459ad4aba610f014d1bf4d))

- Derive compose path from stack_name and retry monitor deletion
  ([`d016014`](https://github.com/chutch3/homelab/commit/d0160149e2cdce282a223b90f5784bf5637ebabd))

- Ensure bitwarden cli is installed and correctly detected during login
  ([`48ae33f`](https://github.com/chutch3/homelab/commit/48ae33ff9990b43c57026167ef7d2d416defa35f))

- Ensure secret_provider variable is loaded and rename reserved 'action' variable
  ([`0f6132d`](https://github.com/chutch3/homelab/commit/0f6132d4debb14b4433f7e6d6982ccdc6a10a1b5))

- Exclude older machines from the the claudecode deployment
  ([`ff2f7b9`](https://github.com/chutch3/homelab/commit/ff2f7b91dae2350f7d4a18041fb1f58c45bf6fdb))

- Improve storage safety and document mount race condition
  ([`74008d1`](https://github.com/chutch3/homelab/commit/74008d13fe652430de3a9d7eb4a9cd4beb677ecb))

- Install ansible collections project-locally for consistent resolution across environments
  ([`f5f1c22`](https://github.com/chutch3/homelab/commit/f5f1c226b6f727a86c231416e4b49ba483ad2e39))

- Install ansible galaxy collections as part of install task
  ([`8e63d68`](https://github.com/chutch3/homelab/commit/8e63d680c51cf5aa47294dc60c93dbe1eb49b480))

- Load docker context before removing stacks in repair and teardown
  ([`c9d848d`](https://github.com/chutch3/homelab/commit/c9d848da7749c66553015849e8633760ffcb4f2d))

- Pass active docker context endpoint to community.docker modules
  ([`bdb46b6`](https://github.com/chutch3/homelab/commit/bdb46b647c2be8a4f33087f36eb280a397701f77))

- Pass registry credentials when deploying stacks
  ([`7ebbef1`](https://github.com/chutch3/homelab/commit/7ebbef1309df6635af8d23b7747d281350723896))

- Publish Technitium port 5380 in host mode
  ([`e4cc45b`](https://github.com/chutch3/homelab/commit/e4cc45bb5580120ae74070919419b4c492920056))

- Publish Traefik ports in host mode and switch update order to stop-first
  ([`66e9253`](https://github.com/chutch3/homelab/commit/66e9253ffd5524f908a3a0cd670aa5098b72e8de))

- Remove non-boolean when conditions on DNS and uptime flag tasks
  ([`3124741`](https://github.com/chutch3/homelab/commit/312474184a6edb5d71bb541d3bb3522314338ea1))

- Remove sabnzbd hostname and add accepted statuscodes for uptime monitor
  ([`6faf45f`](https://github.com/chutch3/homelab/commit/6faf45f2d38bbc855d82a90fa7d8a67d5673beba))

- Remove silent defaults in favor of explicit validation
  ([`6b21193`](https://github.com/chutch3/homelab/commit/6b21193a25691d6b2d564578c465c68eb151bbe7))

- Remove traefik exposure from cicd runner and drop unused network
  ([`d3f4146`](https://github.com/chutch3/homelab/commit/d3f41460f1620629cee04e332be4670cb76d573e))

- Removed ignoring output for bitwarden adapter
  ([`ae5dc01`](https://github.com/chutch3/homelab/commit/ae5dc01c310f41958c82a1e045ddc23d28990678))

- Replace pip3 and poetry with uv across Taskfile and docs workflow
  ([`0676110`](https://github.com/chutch3/homelab/commit/0676110dae32e53e40e945cf26fc3f3038c2b857))

- Replace poetry with uv in ci pipeline
  ([`0e6e79c`](https://github.com/chutch3/homelab/commit/0e6e79c9d903247fcf485bdfc361e0c18ce4347e))

- Retry uptime kuma login on socket.io connection failure
  ([`b7c5e1c`](https://github.com/chutch3/homelab/commit/b7c5e1c5fafa12fb128ffbaf75d4bfd20ae81c66))

- Run docker stack/network operations on localhost via docker context
  ([`b2e942c`](https://github.com/chutch3/homelab/commit/b2e942cb60bc9891f5d99cdbe222b148f38b67f4))

- Skip Uptime Kuma steps gracefully when service is unreachable
  ([`85cfac1`](https://github.com/chutch3/homelab/commit/85cfac1354a28615cc47c8b9085874b5c831a9b3))

- Source existing bw session before status check in secrets:login
  ([`52db98d`](https://github.com/chutch3/homelab/commit/52db98dd22ecced33422261c3842cecac950a9dd))

- Stop docker before iSCSI unmount and run stack removal on the manager
  ([`65892dd`](https://github.com/chutch3/homelab/commit/65892ddfe3013ee64b5ba1b1fd802ee98ce5b37a))

- Sync vault before secrets operations to prevent stale cache and session issues
  ([`25cd92f`](https://github.com/chutch3/homelab/commit/25cd92f2cacd635ad77cd4537c2d68c799a0f88a))

- The devbox image
  ([`044d987`](https://github.com/chutch3/homelab/commit/044d987e8d404803f4fe8bd7caaf56fe3c90f3f9))

- Use cli_context for docker_stack modules and capture context name in get-docker-host
  ([`f3e470a`](https://github.com/chutch3/homelab/commit/f3e470ae95549979ce0c987bf535404b8ab4f940))

- Use dnsrr on Loki to bypass broken IPVS VIP routing
  ([`cab7729`](https://github.com/chutch3/homelab/commit/cab77291d8d1aa053bbea2c630d77a1d7614aab8))

- Use lookup plugin to read .env from controller instead of remote host
  ([`253058c`](https://github.com/chutch3/homelab/commit/253058c8ffc30e48fbbad4d07c6cba674e2ffb58))

- Use separate execute timeout for ssh_execute_script to allow long-running remote commands
  ([`c17f419`](https://github.com/chutch3/homelab/commit/c17f419bba804aea299c9c9a6e0f3ad693e66541))

- Use system python3 as default ansible interpreter
  ([`1bd1f4f`](https://github.com/chutch3/homelab/commit/1bd1f4f7725acec5d0a6ec2dd79b6df5df4afa91))

- Use uv run for ansible commands instead of hardcoded venv paths
  ([`a8eed5e`](https://github.com/chutch3/homelab/commit/a8eed5e5a4728161db909ac3d839db712be7f8fe))

- Use venv ansible-lint and ansible-playbook in pre-commit hooks
  ([`931f996`](https://github.com/chutch3/homelab/commit/931f996ba9d79085e2fdd056f306889db64b1a1e))

### Build System

- Add pytest-httpserver dev dependency
  ([`0e7c429`](https://github.com/chutch3/homelab/commit/0e7c4296fca6cf1f4f69dc8f466143ebbda16e1b))

### Chores

- Removed the old .cursor directory
  ([`927e7c6`](https://github.com/chutch3/homelab/commit/927e7c672dd8b167ecf374b5aad990ad3a1155b6))

### Documentation

- Sync documentation with recent service and configuration updates
  ([`0fc4259`](https://github.com/chutch3/homelab/commit/0fc42595e18093525bf1415262e7dfc88058ae7a))

### Features

- Add claudecodeui, code-server, and devbox development tools
  ([`2f90341`](https://github.com/chutch3/homelab/commit/2f9034122e6e3001cee2d046c2a4a685764cc035))

- Add docker cli to devbox
  ([`037eb66`](https://github.com/chutch3/homelab/commit/037eb666118728f2692a194e4c848a0c6b821464))

- Add dotnet, rust, kubectl, ansible, tmux, fzf, jq, yq and gpu support to devbox
  ([`53939dc`](https://github.com/chutch3/homelab/commit/53939dcbdc703a4f92c46930cea2e13e7ac589f5))

- Add network repair tools and improve swarm deployment reliability
  ([`1fc951a`](https://github.com/chutch3/homelab/commit/1fc951a9d4e941c1e719df3443dcc1227a1c8b8a))

- Add validation and helpful error messages to secrets role
  ([`025f39e`](https://github.com/chutch3/homelab/commit/025f39ec651b8382028a2f4e9c31f3b6969f6a38))

- Added budget mcp and task to base image
  ([`82627ec`](https://github.com/chutch3/homelab/commit/82627ecc6e3bfddebea3c02a396188d63ecaf5a7))

- Added hosts and ssh configs to the secrets sync
  ([`11f95e7`](https://github.com/chutch3/homelab/commit/11f95e7678b8b7a856b4e6bd09c9be548f1d6844))

- Bump radarr
  ([`82cd272`](https://github.com/chutch3/homelab/commit/82cd27243179943cb07edef0960a8f646162daf2))

- Implement secret orchestration layer for .env sync and restore
  ([`bb694f7`](https://github.com/chutch3/homelab/commit/bb694f79018a347f6d6d07d0b081224b849b058f))

- Migrate python tooling from poetry to uv, add pre-commit and go-task to devbox, add actual-mcp
  service
  ([`7fa056e`](https://github.com/chutch3/homelab/commit/7fa056ee09874d61fc302bbc04d3c3807966231e))

- Pass CLI_ARGS to devbox docker build task and remove unused deploy tasks
  ([`aee636c`](https://github.com/chutch3/homelab/commit/aee636caa281b6f02f38200fce56b5e963c95811))

- Set actual-mcp to read-only mode
  ([`b51930d`](https://github.com/chutch3/homelab/commit/b51930df643530b79bee341c543b04a339c5a711))

- Store secrets as bitwarden file attachments with full push/pull workflow
  ([`f85c4df`](https://github.com/chutch3/homelab/commit/f85c4dfeb955074f2d265aee564b02f53d4ee645))

- Support uptime_kuma.path and accepted_statuscodes labels for per-service monitor configuration
  ([`8631f44`](https://github.com/chutch3/homelab/commit/8631f44cb39157cbed996e96995a1e2ce4e31b96))

- Sync ansible hosts and ssh config files alongside .env in secrets push/pull
  ([`647bbb3`](https://github.com/chutch3/homelab/commit/647bbb311c21745d2ca789ae4d4a75a1cb592c0b))

### Refactoring

- Remove manga_volume_migrator. the tranga fork now handles volmes better
  ([`b9ab855`](https://github.com/chutch3/homelab/commit/b9ab855a164842c9c342d5d996e8167adb39c59b))


## v3.13.0 (2026-05-11)

### Bug Fixes

- Allow subnet-routed LAN traffic in ACL and document troubleshooting
  ([`a630ec4`](https://github.com/chutch3/homelab/commit/a630ec47bd557559a84a83090eca9b1c61df17f7))

- Always ensure tailscale apt repository is configured
  ([`3af4132`](https://github.com/chutch3/homelab/commit/3af41325517ba121ce9c0678068c0c25c548b238))

- Default GITHUB_REPO to homelab in runner REPO_URL
  ([`c35fc18`](https://github.com/chutch3/homelab/commit/c35fc18b786ef66489e99c1e5895c3f73f3949ef))

- Guard tailscale version display against empty stdout in check mode
  ([`6a97cb4`](https://github.com/chutch3/homelab/commit/6a97cb4fb5df8bba9c5afa07e33436b0d8dc26ab))

- Prevent cluster nodes from accepting tailscale dns overrides
  ([`9733acf`](https://github.com/chutch3/homelab/commit/9733acf860515403f25ac68134f278fe9b34af9a))

- Publish DNS port 53 with mode host to prevent Swarm ingress DNAT hijacking
  ([`e7866a2`](https://github.com/chutch3/homelab/commit/e7866a2ca4e1b8c362d214671073b7f6af185fb3))

- Register github-runner at org level using ORG_NAME instead of REPO_URL
  ([`d610f24`](https://github.com/chutch3/homelab/commit/d610f24aea39f33eff013a95a83675880bdb6311))

- Revert to REPO_URL for repo-level runner registration on personal GitHub accounts
  ([`a9a7276`](https://github.com/chutch3/homelab/commit/a9a7276c0ddf4a529d6f7d58d2f9d76260c47acb))

- Rewrite ACL policy as valid HuJSON with native line comments
  ([`420fd0b`](https://github.com/chutch3/homelab/commit/420fd0bfe3559eb27a5498062270531549802972))

- Show subnet routes and health warnings in tailscale status
  ([`cbcfff7`](https://github.com/chutch3/homelab/commit/cbcfff7ce0362fc1c640779152c1065f15d9cd5e))

- Skip tailscale auth assert and up command in check mode
  ([`1a12164`](https://github.com/chutch3/homelab/commit/1a121640e87ee40f34c712d685d3280d8f17e43f))

- Use app-specific env vars for takeout-manager image registry
  ([`cf46170`](https://github.com/chutch3/homelab/commit/cf46170b3d631570b3a69fddefbe4f0f1fe35b5f))

### Documentation

- Add Tailscale VPN user guide
  ([`c5d952a`](https://github.com/chutch3/homelab/commit/c5d952aeb90d9ad68c53e5dd876131311f30b143))

- Clarify split DNS setup deploys to all nodes not just manager
  ([`22c8f61`](https://github.com/chutch3/homelab/commit/22c8f610e509d1b29023f33668155c4a0db6e6c7))

- Document Docker Swarm port 53 DNAT hijacking and resolution steps
  ([`589edad`](https://github.com/chutch3/homelab/commit/589edad08c883b7139d6d1232de2fd8679544089))

- Document trust model, LAN device access, and subnet routing
  ([`3a017b6`](https://github.com/chutch3/homelab/commit/3a017b6b5d1bd3bfe1867cbddcd337a05a438e86))

- Sync roadmap with recent deployments and ops improvements
  ([`a747203`](https://github.com/chutch3/homelab/commit/a747203c47dab464d68660aa909960c61bcae343))

- Update auth key instructions to match current Tailscale UI
  ([`e8ccd6e`](https://github.com/chutch3/homelab/commit/e8ccd6e023ef013233aa10f853038a41c7657387))

### Features

- Add monitoring task include and fix registry login
  ([`aa43340`](https://github.com/chutch3/homelab/commit/aa43340310bd5b01b480b65643d982d537e27b55))

- Add optional Tailscale role with drift detection, health check, and ACL policy
  ([`194e099`](https://github.com/chutch3/homelab/commit/194e0991d362bf395717ce00f5043f3b95776636))

- Added freshrss
  ([`c117a08`](https://github.com/chutch3/homelab/commit/c117a0834885f80dab6730c8ee3ebc7637641d4d))

- Allow Tailscale CGNAT range in Technitium recursion for split DNS
  ([`d637f2f`](https://github.com/chutch3/homelab/commit/d637f2fd274960130fc73b39edc0d27d69f7bec3))

- Bump actual_server
  ([`b9e04a8`](https://github.com/chutch3/homelab/commit/b9e04a84b40877e8a8990d4170da1a03529b36d0))

- Move iperf3 images to GHCR and pin apk version to 3.19.1-r1
  ([`327a840`](https://github.com/chutch3/homelab/commit/327a84059450e7768a9679cf9d0d97a1997a1805))

- Updated logs to help better identify issues that cause crashes in the homelab
  ([`923cd9f`](https://github.com/chutch3/homelab/commit/923cd9fc2a5fdd3c6dbb3b9d638079215c799d65))

### Refactoring

- Cleanup takeout-manager code
  ([`9728d47`](https://github.com/chutch3/homelab/commit/9728d47f0b997d72e4095a96a38b81d65a58a951))

- Move tailscale ACL policy to role root
  ([`88c43d5`](https://github.com/chutch3/homelab/commit/88c43d53e04b58979249612f94d76623e369ca60))


## v3.12.0 (2026-05-04)

### Bug Fixes

- Address review findings — remove dead health playbook, clarify reboot vs recover, add drain-node
  guard, rename duplicate panel, document provisioning path separation
  ([`e8c1abc`](https://github.com/chutch3/homelab/commit/e8c1abc86821cc1457cea6cdb4d3a65f89fd3d97))

- Correct delegate_to, manager_hostname, and secondary token guard in DNS role
  ([`fdab6ab`](https://github.com/chutch3/homelab/commit/fdab6abd8b2104a810a47bdf07f34b3e85277036))

- Guard adapter display tasks against check mode skipped uri results
  ([`bd2a89c`](https://github.com/chutch3/homelab/commit/bd2a89c2022ea7601392f3c5aea77bb8bdced922))

- Move local dashboards bind-mount outside NAS provider path to resolve duplicate UID provisioning
  conflict
  ([`7d55427`](https://github.com/chutch3/homelab/commit/7d554271504a06386cd83d5bcfb0b52995caebc0))

- Pass SSH_KEY_FILE to ssh and scp calls in omv.sh
  ([`7f0cbcc`](https://github.com/chutch3/homelab/commit/7f0cbcc94392db497e219b2481d24bd93b698ecb))

- Retry apk install of dante-server on transient network failure
  ([`5444979`](https://github.com/chutch3/homelab/commit/544497954e248144855d73289e7af67c289ddd36))

- Warn when SSH_KEY_FILE falls back to default in ssh.sh
  ([`6110ac4`](https://github.com/chutch3/homelab/commit/6110ac4f4ec7d66de4610334a2d56290511699f0))

### Chores

- Bumped technitium dns version
  ([`42054a6`](https://github.com/chutch3/homelab/commit/42054a6c9a5eee066a52d25c92f1c05a567dd883))

- Include tests/unit/scripts in test tasks
  ([`e1b82a3`](https://github.com/chutch3/homelab/commit/e1b82a3f61c3120a20edff0952d7e8793b81a62f))

- Mark SSH_KEY_FILE as required and fix default in env.example
  ([`380c9af`](https://github.com/chutch3/homelab/commit/380c9aff2edcb2ca18242b40124f2964ed7fe29e))

- Migrate stack to current official compose baseline
  ([`b3c525a`](https://github.com/chutch3/homelab/commit/b3c525aa166ff95f49e76451754be9bedb7846b8))

- Set tranga naming scheme for volume subdirectory organization
  ([`7f43a91`](https://github.com/chutch3/homelab/commit/7f43a91e881c1ab44d1e72f50e0ce13329cb9828))

- Standardize shell script shebangs and safety flags
  ([`6e488ae`](https://github.com/chutch3/homelab/commit/6e488aeb3d26c36cfda4643604feaba2c35ac259))

- Switch tranga to ghcr.io fork image and bump settings config version
  ([`c1ea849`](https://github.com/chutch3/homelab/commit/c1ea8493fd257170412f1228b97a75e1d1478ccc))

### Documentation

- Update README to reflect hardened implementation
  ([`b3de45f`](https://github.com/chutch3/homelab/commit/b3de45f59d6f9cecaa2800aafbba5fac90fcee37))

- Update SSH setup instructions and group_vars path references
  ([`f495046`](https://github.com/chutch3/homelab/commit/f49504678b0c92375d0c775a55bfbbd2d7b8d57b))

### Features

- Add ansible:ssh:generate and ansible:ssh:distribute tasks
  ([`2e9bb4f`](https://github.com/chutch3/homelab/commit/2e9bb4f759152551fe0caa8c5e138ff32425153f))

- Add cluster health check script covering node states, replica counts, DNS crashes, and gossip
  instability
  ([`fd275a0`](https://github.com/chutch3/homelab/commit/fd275a05e09c1858089581d461bd2ca6ecd6e538))

- Add Grafana cluster health dashboard with node availability, container health, and Loki log panels
  ([`7b302db`](https://github.com/chutch3/homelab/commit/7b302dbd393c1078f42e1da12da02f62960f0ad3))

- Add manga_volume_migrator to reorganise chapters into volume subdirectories via MangaDex and
  Tranga
  ([`af5f91d`](https://github.com/chutch3/homelab/commit/af5f91daf4bbb2c04cb4b29ca87e72bcffe2cd68))

- Add safe single-node reboot playbook with drain, storage unmount, and redeploy phases
  ([`f105861`](https://github.com/chutch3/homelab/commit/f105861d2744da01783d6b61aba283004c1cfd9f))

- Added komga and tranga (to the downloads stack)
  ([`d461e50`](https://github.com/chutch3/homelab/commit/d461e500d9eb6e97afe0bfaf86602f512fdc6461))

- Make DNS provider pluggable via primary/secondary adapter pattern
  ([`596d4c7`](https://github.com/chutch3/homelab/commit/596d4c7d225f682c0a6c8c2a0ba0d44f330ef045))

- Make NAS SSH user configurable via NAS_USER
  ([`7356689`](https://github.com/chutch3/homelab/commit/7356689ac85517d9ded14acc8e179458808ed067))

- Update tranga naming scheme to standard volume/chapter format
  ([`aa45021`](https://github.com/chutch3/homelab/commit/aa450215c747be9bc88f1c9c80d09c6651df0dcf))

### Refactoring

- Clean up and harden common scripts
  ([`9fee82f`](https://github.com/chutch3/homelab/commit/9fee82fa4a5563bfe7665b8618e2886f33ecf336))

- Convert group_vars/all to directory structure and remove dead secrets config
  ([`29d1eef`](https://github.com/chutch3/homelab/commit/29d1eefe47ea03446bb119d5ba7fce4831378185))

- Fix shebang and set flags in init-secrets and clean-secrets
  ([`44b9014`](https://github.com/chutch3/homelab/commit/44b901452414dd99d0f1f324bdb897b35cb7cdf8))

- Harden sync-nas-cert.sh and docker-compose
  ([`ea5b495`](https://github.com/chutch3/homelab/commit/ea5b4957698b0ed44045be2f36251b53ca84b316))

- Remove dead function and deduplicate user@host in omv.sh
  ([`798eb4a`](https://github.com/chutch3/homelab/commit/798eb4aae8ea457ce0259fa72f11950e2245c9e2))

- Standardise test file names to snake_case
  ([`beb0d9a`](https://github.com/chutch3/homelab/commit/beb0d9ac5e3c7c74f8e7aac9f641d0260ec9bb0e))

### Testing

- Move common script tests to tests/unit/scripts
  ([`2969dd0`](https://github.com/chutch3/homelab/commit/2969dd0329d9286675cc53579eb79eac2beed324))


## v3.11.0 (2026-04-27)

### Bug Fixes

- Sync-nas-cert secret and infinite retry loop
  ([`414757f`](https://github.com/chutch3/homelab/commit/414757fa1540e76cf0aad9983e1241f259ed3375))

### Features

- Added excalidraw
  ([`ab0ff75`](https://github.com/chutch3/homelab/commit/ab0ff7569aa5d2519812a1dfc3a5270d7d2e785d))

- Added excalidraw storage
  ([`7321a6c`](https://github.com/chutch3/homelab/commit/7321a6cd9e7a32d417269b899038c51e79a0a4cf))

- Added newtarr
  ([`fa4131c`](https://github.com/chutch3/homelab/commit/fa4131c1e665478416bf74699f4323f98ffa16bb))


## v3.10.0 (2026-04-20)

### Bug Fixes

- Correct cryptpad volume mounts, config path, and healthcheck
  ([`2f546df`](https://github.com/chutch3/homelab/commit/2f546df83d7e95435b36993839a529d31dc7813a))

- Set iscsi node.startup=automatic during bootstrap so targets reconnect on reboot
  ([`d8ae518`](https://github.com/chutch3/homelab/commit/d8ae51834f3f8b8ac253a3245e38978caf43a3a3))

- **ansible**: Add retry logic and increase timeouts for uptime kuma monitors
  ([`3ca7474`](https://github.com/chutch3/homelab/commit/3ca7474fe7555f84ddc7a216aac19c6593cc0bfb))

- **storage**: Add docker systemd drop-in to prevent race with iscsi mounts on boot
  ([`00cb379`](https://github.com/chutch3/homelab/commit/00cb3796be56a9f1913f7f38a09beb5864b46812))

### Features

- Update the prefect stack
  ([`711e44c`](https://github.com/chutch3/homelab/commit/711e44c33fbca689f76770248ab8db438eb954f8))

- **immich**: Relocate to photos nodes with dedicated postgres storage
  ([`018fcfe`](https://github.com/chutch3/homelab/commit/018fcfeaab0392e40784df07fb500a26cbb65e36))


## v3.9.0 (2026-03-30)

### Bug Fixes

- Documentation deployment condition
  ([`f97aade`](https://github.com/chutch3/homelab/commit/f97aadeb8a9f28c0b05b2bbdf9d04d51c5e606ab))

- Pin docker version across swarm nodes to prevent version skew and libnetwork crashes
  ([`8bd7f13`](https://github.com/chutch3/homelab/commit/8bd7f13e4f4206b8fca51e173349bae1e7d55428))

### Documentation

- Overhaul documentation structure and refactor navigation
  ([`862529f`](https://github.com/chutch3/homelab/commit/862529f4cbb31fd2d763027707c3e2151999609b))

- Rename project from Selfhosted to Homelab across documentation and configuration
  ([`21e24e6`](https://github.com/chutch3/homelab/commit/21e24e6b3007ee1680ee85d168e3de1a16831b8f))

### Features

- Add Forgejo and GitHub Actions runner stacks and update docs
  ([`c36be9b`](https://github.com/chutch3/homelab/commit/c36be9b07c1d3c268902ada62bad0bd6a95d6459))

- Added ollama for local llm support
  ([`4c5e852`](https://github.com/chutch3/homelab/commit/4c5e852dac902dd46c83f2550958866c15ade36a))

- Added prefect
  ([`7a63292`](https://github.com/chutch3/homelab/commit/7a632928e269ab60b91735d55080882698d8cad9))


## v3.8.0 (2026-03-23)

### Bug Fixes

- Configure Loki to listen on all interfaces instead of localhost
  ([`082cc20`](https://github.com/chutch3/homelab/commit/082cc205bdb7eeb2891085d3daa56c72eda5b742))

- Correct cmd task description and HOST default quoting
  ([`4e59ef2`](https://github.com/chutch3/homelab/commit/4e59ef28b64d08264d68f75d4e25128294ab445a))

- Extract iscsi-login, fix unmount order, and start OCFS2 services before mount
  ([`acce6a4`](https://github.com/chutch3/homelab/commit/acce6a4243ae35b053f64baf676ffe47a089c512))

- Force lazy-unmount all OCFS2 mounts before stopping cluster
  ([`fb4b089`](https://github.com/chutch3/homelab/commit/fb4b0897cee3126862a9c4d20f07a75a3193b640))

- Pin explicit UIDs to Grafana datasources and update dashboard panel
  ([`2c67b73`](https://github.com/chutch3/homelab/commit/2c67b73839f96cdf9d0018f80b4a044fd03df03a))

- Resolve ansible-lint violations in cluster playbook and swarm role
  ([`f0c00e7`](https://github.com/chutch3/homelab/commit/f0c00e70e266903413765edbb71c73e3abaf9133))

- Run DNS and uptime cleanup before stack removal in teardown
  ([`bb18ad7`](https://github.com/chutch3/homelab/commit/bb18ad75ce3708904b0d937d9b4493818b9911c6))

- Update DNS removal to handle infrastructure stacks correctly
  ([`d66abf1`](https://github.com/chutch3/homelab/commit/d66abf1661ad7c76da9a6b5e2582408e4eba328f))

- **dns**: Guard Pi-hole result loops against undefined/missing status attributes
  ([`0785146`](https://github.com/chutch3/homelab/commit/078514624689df0493f0762effedc8a54a3edd33))

- **immich**: Exclude database nodes from server placement and use env vars in healthcheck
  ([`e4072a5`](https://github.com/chutch3/homelab/commit/e4072a574bf2a89e1dda3426395709936b80619e))

- **teardown**: Skip Uptime Kuma steps when tearing down reverse-proxy stack
  ([`1472b3d`](https://github.com/chutch3/homelab/commit/1472b3d59b9b2a1e973012063999af914dac624b))

### Continuous Integration

- Fix a bug in the documentation build and deploy job
  ([`07b2d70`](https://github.com/chutch3/homelab/commit/07b2d70448c4e5d14e784c288e56566160ca99ad))

### Features

- Add DNS API readiness polling before record registration on dns
  ([`6d52b07`](https://github.com/chutch3/homelab/commit/6d52b070f8837fde70bdfa214a170e893d0358df))

- Add docker Python SDK dependency for community.docker collection
  ([`74b7605`](https://github.com/chutch3/homelab/commit/74b7605c67b4a9e80226a7859ec0881d5727be39))

- Add kolibri stack with custom OIDC image build and consolidate registry tasks
  ([`28c1eee`](https://github.com/chutch3/homelab/commit/28c1eeebae8b79f16432f6bd4bbdc528e5dcb5c0))

- Add storage repair playbook and task for OCFS2 fsck recovery
  ([`d1c7367`](https://github.com/chutch3/homelab/commit/d1c736788964d897eecebc36bf0b82f8c577824c))

- Add swarm role tasks for stack and node management
  ([`ef50487`](https://github.com/chutch3/homelab/commit/ef504873e7ef4dfb130dff90a7003e24412b5d9b))

- Add system-logs Grafana dashboard
  ([`215c3b3`](https://github.com/chutch3/homelab/commit/215c3b30648387736fc44ca92342f2573b9fb651))

- Add systemd journal log collection to promtail with persistent positions
  ([`bf79a54`](https://github.com/chutch3/homelab/commit/bf79a5410f1ec7fdd2f4bd3c0d45a480c65f9d2c))

- Register and remove Pi-hole A record and fix compose path lookup
  ([`bd79d91`](https://github.com/chutch3/homelab/commit/bd79d918458464cba8e0f9847aedf06e16fb8781))

- Update repair-storage to gracefully remove and redeploy stacks
  ([`64aae9f`](https://github.com/chutch3/homelab/commit/64aae9fcc51bfb732c44a32867116b930d209236))

- **dns**: Fetch Pi-hole token before DNS registration when secondary DNS is enabled
  ([`630902e`](https://github.com/chutch3/homelab/commit/630902e92b78e9f91cb74d21f68cd66b5c35769a))

- **gpu**: Add driver mismatch detection with auto-reboot and CDI config generation
  ([`76f42cf`](https://github.com/chutch3/homelab/commit/76f42cfeecba3e79a65124da7a46b0d6d31ffd29))

### Refactoring

- Extract iSCSI login steps into shared task file and fix mount
  ([`e10a68c`](https://github.com/chutch3/homelab/commit/e10a68c5889ef3afefd11141106e4568081aa993))

- Move teardown to top-level playbook and add remove-stacks role task
  ([`93c7ae2`](https://github.com/chutch3/homelab/commit/93c7ae2087c58b9f24a6b8e45b3e24aa06e3c91f))

- Simplify Taskfile with new deploy/teardown task interface
  ([`29a9994`](https://github.com/chutch3/homelab/commit/29a9994515000b2392b20de43ca81382131e2e2c))


## v3.7.0 (2026-03-18)

### Bug Fixes

- Home assistant hubitat service endpoint
  ([`a3d9e95`](https://github.com/chutch3/homelab/commit/a3d9e95732c2dc01911cbcbe9e1dd022e5223207))

- When teardown of dns stack skip dns registration removeal
  ([`f95e8a7`](https://github.com/chutch3/homelab/commit/f95e8a7ac2022ae2fdec7be4e5c6984fd9cf74aa))

### Chores

- Clean up .env.example
  ([`917b88c`](https://github.com/chutch3/homelab/commit/917b88c19724d1979496929b8145cb1322fcaa5f))

- Simplified README.md
  ([`ac551a0`](https://github.com/chutch3/homelab/commit/ac551a06a619f55ef3520e334f807e1ae42922f8))

### Continuous Integration

- Docs now in sync with release so that they are in lock step
  ([`0f456d9`](https://github.com/chutch3/homelab/commit/0f456d939bc1baf050acf5757ac6daa34f4b159f))

### Documentation

- Added troubleshooting for stale entries in the overlay networks ARP table
  ([`c27c895`](https://github.com/chutch3/homelab/commit/c27c895a531a1d17ab94899fd77f20c6123543e5))

- Updated the docs
  ([`b00c461`](https://github.com/chutch3/homelab/commit/b00c4612cba8fdb9f816a01e1c7967fee3703311))

### Features

- Add Pi-hole secondary DNS sync
  ([`604581f`](https://github.com/chutch3/homelab/commit/604581fe653590e6f52147698a812141fc82234c))


## v3.6.0 (2026-03-16)

### Bug Fixes

- Correct base_domain variable name and add orphaned container cleanup to teardown
  ([`56e352f`](https://github.com/chutch3/homelab/commit/56e352fbae2f42df2fce8a1a5b49d0336703f0d3))

- Correct CIFS mounts and remove incompatible watchtower after NAS rebuild
  ([`ed8cefe`](https://github.com/chutch3/homelab/commit/ed8cefef7cc74790e86547c00ff11549cb505173))

- Replace deprecated uptime_kuma api module, fix dns regex, and remove ssh password auth enforcement
  ([`d11c937`](https://github.com/chutch3/homelab/commit/d11c93703be13a65c5132f5bc87b220cca1b3522))

- Use venv ansible binaries in taskfile and pin collection versions
  ([`eaeeec8`](https://github.com/chutch3/homelab/commit/eaeeec81d4e6b4db05e4da658e6ba02ee7658b8b))

### Chores

- Update emby to 4.10.0.5, fix cert-sync mode format
  ([`0f585d9`](https://github.com/chutch3/homelab/commit/0f585d95b7ff96c032166f5660c74bca2c9b71b4))

### Documentation

- Updated documentation
  ([`2ae0f58`](https://github.com/chutch3/homelab/commit/2ae0f5843b0351133c59783b1e84d6c159d249c7))

### Features

- Add cluster teardown, iSCSI reconfigure, and NAS IP fix playbooks
  ([`4b9d89b`](https://github.com/chutch3/homelab/commit/4b9d89b0d1c0655e4c9def86af1b5fddbdeb4293))

### Refactoring

- Move iSCSI setup from common role to dedicated storage role
  ([`12d6279`](https://github.com/chutch3/homelab/commit/12d62798793d8f3d1694cc76c586bd35e0fd87e2))


## v3.5.0 (2026-02-02)

### Bug Fixes

- Task command fixes
  ([`9dc04f5`](https://github.com/chutch3/homelab/commit/9dc04f513491fe1e8c15700e609dcc6ab5bdc942))

### Documentation

- Added copy button to code snippits
  ([`6193efd`](https://github.com/chutch3/homelab/commit/6193efd5527c0bc446a9479358a8d5d7cc077e71))

- Documentation and readme improvments
  ([`7413e80`](https://github.com/chutch3/homelab/commit/7413e8050d70b6100698a3f69de28b7b7049cce5))

- Documentation updates
  ([`2c379d2`](https://github.com/chutch3/homelab/commit/2c379d20ede19912b719a2ab9d921882e75c13e6))

- Documentation updates
  ([`a0f5229`](https://github.com/chutch3/homelab/commit/a0f522943ec5d18fb87f2105b93c8859690b5efe))

- Updated kopia docs
  ([`7f98840`](https://github.com/chutch3/homelab/commit/7f988404ea7b1ebe15083fb20c9be72c587fbbf0))

### Features

- Added forgejo with authentik setup doc
  ([`fc5f54c`](https://github.com/chutch3/homelab/commit/fc5f54cb406e36cbcee79fa9502bec809f529494))

- Added new ansible tasks to bettwe support creating and teardown
  ([`4e15db1`](https://github.com/chutch3/homelab/commit/4e15db1a17f3cebaf2bdebc409d75f143295d956))

- Updated ansible deployment and teardown interfaces to include dns and uptime
  ([`ef498ad`](https://github.com/chutch3/homelab/commit/ef498ad1fd505bbcbe27f7e46f04658c91eced21))


## v3.4.0 (2026-01-26)

### Documentation

- Updated documentation
  ([`ccfc466`](https://github.com/chutch3/homelab/commit/ccfc466b571002fba4a6b118ec7724f3469a80db))

### Features

- Add takeout-manager service for Google Photos automation (closes #73)
  ([`0af52be`](https://github.com/chutch3/homelab/commit/0af52becc937228198beac52426fbb02aed1df5b))

- Added initial authentik integration for homelab SSO
  ([`d302c3e`](https://github.com/chutch3/homelab/commit/d302c3e9a5abe3d6194c1cfb46de98cc6c55262f))

- Added kopia for backups of the iscsi mounts
  ([`cbcbe09`](https://github.com/chutch3/homelab/commit/cbcbe09079dc3bee320b05bd3b0a94c2f4d57dea))

### Refactoring

- Migrated emby to iscsi
  ([`0912c53`](https://github.com/chutch3/homelab/commit/0912c53c326756fc7d362a1f390124ae5a4443bc))


## v3.3.0 (2026-01-19)

### Bug Fixes

- Addressed the whitelist issue with sabnzbd
  ([`173bcb3`](https://github.com/chutch3/homelab/commit/173bcb39fad2696e8665df1d1e4bec227e756ced))

- Home assistant router now setup correctly. HA was migrated to ISCSI
  ([`0f37d7e`](https://github.com/chutch3/homelab/commit/0f37d7ec248d0da639181b118765e2f64175deb8))

- Permission specification, should be an int
  ([`e62f190`](https://github.com/chutch3/homelab/commit/e62f1902bb3ef4e1edbd585417566d79bbc50807))

### Documentation

- Updated roadmap
  ([`06e4392`](https://github.com/chutch3/homelab/commit/06e4392b16666db87c414917d0f9461a408d2523))

### Features

- Added mlflow app
  ([`77b24ab`](https://github.com/chutch3/homelab/commit/77b24ab0bf851aff37e39a6879a7e01fec7189b6))

- Added uptime-kuma registration of all machines and services
  ([`ab4acaa`](https://github.com/chutch3/homelab/commit/ab4acaaa23c17ef580f207fc0d014f2d6c2f5630))

- Moved downloads to iscsi
  ([`79db11e`](https://github.com/chutch3/homelab/commit/79db11eb68be44cbbbad142442efe99e7a381c9a))

### Refactoring

- Cleaned up ansible config env specification
  ([`88a3c55`](https://github.com/chutch3/homelab/commit/88a3c55187b649d6be5d7cc8bb7d17bc82710a25))

- Kiwix no longer has a starter pack
  ([`cbb84d8`](https://github.com/chutch3/homelab/commit/cbb84d8be031c73c6f91d05d79a472ce81de1515))


## v3.2.0 (2026-01-12)

### Bug Fixes

- Added help message if stack not found when deploying
  ([`89cb23b`](https://github.com/chutch3/homelab/commit/89cb23bbbaae4a03813971348af2c1d424c9726e))

- Cryptpad config.js and move to iscsi
  ([`7941bf9`](https://github.com/chutch3/homelab/commit/7941bf99a3d315cc442afdf20e177ae41788b3c1))

- Dns resolution issue with traefik by adding temp env var
  ([`0679f6b`](https://github.com/chutch3/homelab/commit/0679f6b4ddc455bbb09129e93f0d47440d5e9686))

- Formatting the output in teardown all correctly so you can see what apps where torn down
  ([`79ea04a`](https://github.com/chutch3/homelab/commit/79ea04a4638417e9bea5f9e474a96e6a9b99c01a))

- Octals are now defined correctly and linter is fixed
  ([`ae8448a`](https://github.com/chutch3/homelab/commit/ae8448a513f7d613c44398245a85d9bb4da7c8f3))

- Paths not being correct in the deploy stacks
  ([`3484cc4`](https://github.com/chutch3/homelab/commit/3484cc41d6afa1f4bf908caec9f6364fb85ba468))

- Reload o2cb should be restarted
  ([`d14869b`](https://github.com/chutch3/homelab/commit/d14869b11e15e501bde520b0639eee97c56fd791))

- Remove placement constraints from kuma and vaultwarden
  ([`99e9c35`](https://github.com/chutch3/homelab/commit/99e9c358ce1b9c4c6a8d4d08dc9a1d673684cb44))

- Set environment variables before deploying a stack
  ([`983d224`](https://github.com/chutch3/homelab/commit/983d224d06c97b813bd5bf1663b119e1adca51b9))

- The status message in the add service cnames task and lint
  ([`f434b59`](https://github.com/chutch3/homelab/commit/f434b5926d17febbf1fcb2309a196c47128544c7))

### Continuous Integration

- Auto release schedule (every monday at 8 am)
  ([`977586d`](https://github.com/chutch3/homelab/commit/977586dc4b3c7857b14f2ee59d16efde800d9ad2))

### Documentation

- Added troubleshooting markdown file in docs
  ([`4d31378`](https://github.com/chutch3/homelab/commit/4d3137896e20d99c13aaa8796e05b457de82fd44))

- Crt style and mermaid doc fixes
  ([`2a3a19c`](https://github.com/chutch3/homelab/commit/2a3a19c6c4a44f33198fcbc3feffd136a0a76991))

- On how docker handles unresolved domains and it's effect on the private dns service
  ([`41afd7b`](https://github.com/chutch3/homelab/commit/41afd7bdb73af114b36f7413ebb55a00d2d86027))

- Updated roadmap
  ([`a770233`](https://github.com/chutch3/homelab/commit/a7702336d6ddb662e8007faedc69669baff1c098))

### Features

- Added cache ISCSI path in the cluster file system and migrated redis for immich to it
  ([`3a2e1ad`](https://github.com/chutch3/homelab/commit/3a2e1ad45a7bafdeddd4fc8a20acd925c264e565))

- Added mealie
  ([`57051ae`](https://github.com/chutch3/homelab/commit/57051aef779d814e4bd4ec1767a32f4d4cb2b5d2))

- Added node-red
  ([`a7612b2`](https://github.com/chutch3/homelab/commit/a7612b29392b5c3b1fa5910c88e51e7f67a5ef75))

- Added sync functionality for addressing stale nodes (e.g. ip address changes for a node)
  ([`a4a0dc8`](https://github.com/chutch3/homelab/commit/a4a0dc8a1e048fddc9467e52a98962de78c6e3b4))

- Added uptime-kuma
  ([`d7f87fe`](https://github.com/chutch3/homelab/commit/d7f87fe512b66fd2324165853174990d0f5c5ab5))

- Added vaultwarden
  ([`a5a51b4`](https://github.com/chutch3/homelab/commit/a5a51b438243c775f5aaa0ab50a698f58772bd3f))

- Moved uptime-kuma to app-data directory
  ([`51eaf32`](https://github.com/chutch3/homelab/commit/51eaf32da6fa0de1195206185d85d3276cc37602))

### Performance Improvements

- Use dnsrr endpoint mode for prometheus
  ([`ac03e56`](https://github.com/chutch3/homelab/commit/ac03e56fb1c30d550d3b18226d2d202f10e4a9e8))


## v3.1.0 (2026-01-04)

### Bug Fixes

- Cryptpad health check/dns fix, added ssh.sh back
  ([`92dd15d`](https://github.com/chutch3/homelab/commit/92dd15d0be2af723a39d08959d11f51d5059557c))

- Speedtest healthcheck and prometheus exclusion
  ([`65af794`](https://github.com/chutch3/homelab/commit/65af7944dc62478a040ecd0668ae80ed0fd286c9))

- Speedtest healthcheck and update dashboard
  ([`afe5b22`](https://github.com/chutch3/homelab/commit/afe5b227ac0ece6b67fc4cf1c4d36cf49e3dbde7))

- Teardown with volumes now actually works
  ([`84f10c8`](https://github.com/chutch3/homelab/commit/84f10c80b6a88e10df55c6788ea82c1c12097a00))

### Chores

- Added system level pruning of each node as a ansible command
  ([`f2fc6f0`](https://github.com/chutch3/homelab/commit/f2fc6f01076105d6fcb7a460d4377115cc3d507a))

- Ansible-lint now only runs on changed ansible files
  ([`e9318e4`](https://github.com/chutch3/homelab/commit/e9318e44d253fe0133b88e841688bd50fe1a216a))

- Bumped traefik version
  ([`b41d24a`](https://github.com/chutch3/homelab/commit/b41d24a3835287a1173e286fec218d6d23acec9a))

- Fix lint issues
  ([`3346999`](https://github.com/chutch3/homelab/commit/3346999d68c480b8b5ae9f5fcf117ec5680fa60a))

- Switched to cuda image of immich
  ([`01288ed`](https://github.com/chutch3/homelab/commit/01288ed80bad08e526d08ebe4434cd3091023aea))

### Documentation

- Fixed mermaid diagrams
  ([`548f2b2`](https://github.com/chutch3/homelab/commit/548f2b275962058d8d3bec737379df1084dfc049))

- Updated docs to reflect current implementation
  ([`4510b15`](https://github.com/chutch3/homelab/commit/4510b1565a97f05a4aa1a4d50c24cb92889a1df2))

### Features

- Added intra-node and internet bandwidth monitoring
  ([`2f34acf`](https://github.com/chutch3/homelab/commit/2f34acf2d9f57e8023dbf0cab5ac076247854bef))

- Added support for gpus and gpu monitoring
  ([`611dd5d`](https://github.com/chutch3/homelab/commit/611dd5d3c29e84d5ba6e3229aaf2a9d1c9a27c42))


## v3.0.0 (2025-12-29)

### Continuous Integration

- Add write permissions to release workflow for semantic-release
  ([`4055cff`](https://github.com/chutch3/homelab/commit/4055cff9ba6a61b580806319b4ac2c8589064d62))

- Fix broken pipelines
  ([`20d844c`](https://github.com/chutch3/homelab/commit/20d844c45f492a7f46cc15b3c56180819421bfd0))

- Fixed release pipeline
  ([`b8cb9ab`](https://github.com/chutch3/homelab/commit/b8cb9ab6e06702c29d0481733caa88a916d17e12))

- Move release to workflow_dispatch and cleanup other jobs
  ([`b8724ab`](https://github.com/chutch3/homelab/commit/b8724ab6ea9f0862a98ffa9ac87a429fd5e8523e))

### Documentation

- Renamed from selfhosted.sh to homelab
  ([`3ad84b1`](https://github.com/chutch3/homelab/commit/3ad84b180bcf86ea6ab63950738a1da6b80e0447))

### Features

- Switched to ansible and taskfile
  ([`a0b8203`](https://github.com/chutch3/homelab/commit/a0b8203de3ccd0336969fa09a299bce1aa8c488b))

### Breaking Changes

- Deployment system migrated from docker-compose to ansible and taskfile


## v2.3.1 (2025-12-20)

### Bug Fixes

- Traefik network specification, dns web access and bump dns propagtion check delay
  ([`edb7658`](https://github.com/chutch3/homelab/commit/edb76584bab1fa422a44c5e702fdc48683c194cb))

### Refactoring

- **homepage**: Clean up homepage and all the widgets related to it
  ([`85570da`](https://github.com/chutch3/homelab/commit/85570dadc99a5df9041887609f7d9434686ecf51))


## v2.3.0 (2025-12-17)

### Features

- **cert-sync-nas**: Add automated Let's Encrypt certificate provisioning and sync to OMV
  ([`f786c7c`](https://github.com/chutch3/homelab/commit/f786c7c797b11d3c66b92b4417963dce3becbbd3))


## v2.2.0 (2025-12-14)

### Features

- Added immich for comparsion to photoprism
  ([`e0e8aaa`](https://github.com/chutch3/homelab/commit/e0e8aaaa895fbd84f462a0da0cc4fcccd8a22962))

- Added loki and access logging for debugging traefik issues
  ([`18246f9`](https://github.com/chutch3/homelab/commit/18246f9c4bf7f77866c3010ff69079daf8643c20))

### Refactoring

- Merged all download clients into one stack, added vpn container, updated *arr to be local
  (excluding sonarr)
  ([`15ff0f6`](https://github.com/chutch3/homelab/commit/15ff0f6ccbfd6ae6ced70e19f44588ff9550ce97))


## v2.1.1 (2025-12-05)

### Bug Fixes

- Make monitoring test executable and fix shellcheck warnings
  ([`c81a8bf`](https://github.com/chutch3/homelab/commit/c81a8bf871f777c2d8a047f404a714dccec82445))


## v2.1.0 (2025-12-04)

### Chores

- Version bump emby
  ([`3683ab1`](https://github.com/chutch3/homelab/commit/3683ab16ed67e18d90f6ce130e66ac6cd1ae54f1))

### Documentation

- Updated roadmap
  ([`9b39978`](https://github.com/chutch3/homelab/commit/9b39978976e406074bc5f70b9d109d776be0b218))

### Features

- Add Kiwix offline Wikipedia service with permission fix
  ([#59](https://github.com/chutch3/homelab/pull/59),
  [`abc24c4`](https://github.com/chutch3/homelab/commit/abc24c4e81f311d913910a0d941fa2ca2863f04c))


## v2.0.0 (2025-12-03)

### Features

- Refactor and addressing issues ([#58](https://github.com/chutch3/homelab/pull/58),
  [`027820e`](https://github.com/chutch3/homelab/commit/027820e4a85b289c8b485fb63310b79a27a8cb8b))

### Breaking Changes

- Cli completely changed


## v1.4.1 (2025-09-09)

### Bug Fixes

- Broken labeling and formatting ([#56](https://github.com/chutch3/homelab/pull/56),
  [`6c787d4`](https://github.com/chutch3/homelab/commit/6c787d42ad1ac517ae738235b70501d342804839))

- Dns now works correctly ([#56](https://github.com/chutch3/homelab/pull/56),
  [`6c787d4`](https://github.com/chutch3/homelab/commit/6c787d42ad1ac517ae738235b70501d342804839))

- DNS setup and registration and deployment labeling
  ([#56](https://github.com/chutch3/homelab/pull/56),
  [`6c787d4`](https://github.com/chutch3/homelab/commit/6c787d42ad1ac517ae738235b70501d342804839))

- Fixed all remaining ssl and dns issues ([#56](https://github.com/chutch3/homelab/pull/56),
  [`6c787d4`](https://github.com/chutch3/homelab/commit/6c787d42ad1ac517ae738235b70501d342804839))

### Chores

- Cleanup bad rebase ([#56](https://github.com/chutch3/homelab/pull/56),
  [`6c787d4`](https://github.com/chutch3/homelab/commit/6c787d42ad1ac517ae738235b70501d342804839))

- Renamed dns test file ([#56](https://github.com/chutch3/homelab/pull/56),
  [`6c787d4`](https://github.com/chutch3/homelab/commit/6c787d42ad1ac517ae738235b70501d342804839))


## v1.4.0 (2025-09-07)

### Bug Fixes

- Dns and ssl issues ([#52](https://github.com/chutch3/homelab/pull/52),
  [`ad4f2eb`](https://github.com/chutch3/homelab/commit/ad4f2eb0ef8fda97d0bef3de2e502e9144496dec))

- Final cleanup
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Idempotency with dns api calls
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Includes some test and app fixes
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Set TEST=1 in test setup to skip Docker validation
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

### Chores

- Fix pipeline linter errors
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Fixed logging
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Remove Superseded Analysis Files and Configurations
  ([#50](https://github.com/chutch3/homelab/pull/50),
  [`9028ea0`](https://github.com/chutch3/homelab/commit/9028ea07a0b21d7d4936f3eedbd65c745e4d2cb6))

- Update all logging
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

### Continuous Integration

- Added code coverage ([#49](https://github.com/chutch3/homelab/pull/49),
  [`b8edea3`](https://github.com/chutch3/homelab/commit/b8edea3a10114a4666578939b9d62526e11b64b1))

- Fixed the test setup
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Temp removed the code coverage publishing
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

### Documentation

- Removed test count
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Updated the documentation
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

### Features

- Add comprehensive pre-flight validation checks
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Add idempotent overlay network creation functions
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Add node label existence checking and idempotent labeling
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Add worker node swarm membership checking functions
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Docker Swarm Cluster Management - Complete Implementation [closes #39]
  ([#48](https://github.com/chutch3/homelab/pull/48),
  [`659acaa`](https://github.com/chutch3/homelab/commit/659acaa9939a382c65b492ba60fd5d9e2e583b5b))

- Implement idempotent swarm initialization logic
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Implement idempotent worker node joining logic
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))

- Improve .env security support and add configuration guidance [GREEN]
  ([`2ad185e`](https://github.com/chutch3/homelab/commit/2ad185e5a127aa7f3d4a99cbb22c94769a126fbc))

### Refactoring

- Removed dead code
  ([`0073048`](https://github.com/chutch3/homelab/commit/0073048407322be33a2ba4fb4154c277b71abe9f))


## v1.3.0 (2025-08-11)

### Features

- Updated the way environments works and removed homlab.yaml
  ([`9c8d0c3`](https://github.com/chutch3/homelab/commit/9c8d0c381397beb8d5ec005adbfef58bdc3683d2))


## v1.2.0 (2025-08-11)

### Features

- Comprehensive Test Suite for Unified Configuration [closes #40]
  ([#47](https://github.com/chutch3/homelab/pull/47),
  [`a9c1cd7`](https://github.com/chutch3/homelab/commit/a9c1cd75e5c2cabc9ae2fa0cb4b4fb803f33fb0c))


## v1.1.0 (2025-08-11)

### Features

- Add manual trigger capability to documentation workflow
  ([`a6e0192`](https://github.com/chutch3/homelab/commit/a6e0192077995837fcac05a8e6840d61248eeb15))


## v1.0.0 (2025-08-11)

- Initial Release
