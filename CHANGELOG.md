# CHANGELOG

<!-- version list -->

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
