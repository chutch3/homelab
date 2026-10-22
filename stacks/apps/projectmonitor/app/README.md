# Project Monitor — vendored upstream fork

Project Monitor was created by **Pivotal Labs and the original Project Monitor
contributors**. It aggregates CI build status into a dashboard intended for a
shared monitor. This directory contains the application imported from
[`vmware-archive/projectmonitor`](https://github.com/vmware-archive/projectmonitor/tree/2b85d1701007d832cbc4b49aa3c94cbacb076884).

This directory is the imported repository root; its nested `app/` directory is
the standard Rails application directory. Homelab service configuration and task
integration live one level above. See the [repository layout](../README.md#repository-layout)
for the boundary and how upstream history is preserved.

Use the [service README](../README.md) for the supported runtime, database setup,
Swarm deployment, secrets, administrator bootstrap, and test commands. The
application is maintained as part of the homelab monorepo.

## Using the dashboard

Each CI build displayed on the dashboard is a project. Sign in with the account
created by the bootstrap command, then select **Manage Projects** to configure
projects and their providers.

The imported adapters cover CircleCI, Codeship, Concourse, Cruise Control,
Jenkins, Semaphore, Solano/Tddium, TeamCity, Travis CI, and Travis CI Pro. Their
recorded tests preserve existing behavior; compatibility with live provider APIs
must be checked when configuring a project.

- [Adding a project](docs/adding_a_project.md)
- [Displaying project status](docs/displaying_your_projects_status.md)
- [Contributing and running tests](CONTRIBUTING.md)

The files in `docs/adding_a_project/` are also rendered in the application's
project setup interface. They are application content, not obsolete developer
documentation.

## Application configuration

`config/settings.yml` defines the application settings; `config/settings.local.yml`
can override them for local development. The homelab stack supplies database
configuration and secrets through its environment and Swarm secrets. Keep the
tracked `config/database.yml`, which reads that environment.

Password administration uses Devise. The existing optional Google OAuth2 and IP
whitelist settings remain in `config/settings.yml`. The deployed dashboard is
also protected by Authentik; see the service README before enabling webhooks.

## Import and export

The configuration page supports importing and exporting project settings. The
existing Rake commands are also available inside a configured application runtime:

```bash
bundle exec rake projectmonitor:export > projects.yml
bundle exec rake projectmonitor:import < projects.yml
```

These commands need the same database configuration and secrets as the running
application. In Swarm, invoke them through `/app/docker/entrypoint.sh`, as described
for the administrator bootstrap in the service README.

## Upstream history

Obsolete VM provisioning, upstream CI pipelines, Rails 2 launchers, and setup tasks
that overwrite the database configuration have been removed. Their original
versions remain available at the pinned upstream commit linked above.

Cloud Foundry deployment helpers and their tests, legacy scheduler settings,
certificate files, and historical database migrations remain for compatibility
review. They are not the homelab deployment procedure.

## Credits and licenses

Copyright (c) 2018 Pivotal Labs.

Credit for the original application belongs to Pivotal Labs and the
[upstream contributors](https://github.com/vmware-archive/projectmonitor/graphs/contributors).
This homelab fork maintains the dependencies, deployment, and compatibility
tooling. The pinned upstream source above records the origin of the imported code.

The original [BSD license text](LICENSE), [MIT license](MIT.LICENSE) with
Copyright (c) 2010 Pivotal Labs, and [VMware notice](NOTICE) with
Copyright 2022 VMware, Inc. are retained verbatim. Keep these files and third-party
notices with the source and distributions; the production image includes them
alongside this README in `/app`.
