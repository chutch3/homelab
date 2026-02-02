# CHANGELOG

<!-- version list -->

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
