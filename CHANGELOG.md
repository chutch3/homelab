# CHANGELOG

<!-- version list -->

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
