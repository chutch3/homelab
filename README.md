# Selfhosted

**Features • Get Started • Documentation**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)

This project provides an automated, Docker-based self-hosted environment for running services with automated SSL certificate management, reverse proxying, and service orchestration. It's designed to be a simple yet production-ready framework for running your own services.

> **What is self-hosting?**
>
> Self-hosting is the practice of running and maintaining your own services instead of relying on third-party providers, giving you control over your data and infrastructure. For more information, see [r/selfhosted](https://www.reddit.com/r/selfhosted/wiki/index).

## Overview

Project status: **BETA**

### Features

- Automated reverse proxy configuration with Nginx
- Automatic SSL certificate management
- Dynamic service domain management
- Docker-based service orchestration
- Simple service enabling/disabling
- Modular architecture for easy addition/removal of services
- Automated testing and validation
- Pre-commit hooks for code quality
- Monitoring and logging support
- Backup capabilities
- Production-ready security practices

### Tech Stack

| Logo | Name | Description |
|------|------|-------------|
| <img src="https://raw.githubusercontent.com/docker/compose/main/logo.png" width="32"> | [Docker Compose](https://docs.docker.com/compose/) | Container runtime and orchestration |
| <img src="https://nginx.org/img/nginx_logo.png" width="32"> | [NGINX](https://www.nginx.com) | Reverse proxy and load balancer |
| <img src="https://www.cloudflare.com/img/logo-cloudflare-dark.svg" width="32"> | [Cloudflare](https://www.cloudflare.com) | DNS and SSL certificate management |
| <img src="https://github.com/acmesh-official/acme.sh/raw/master/wiki/logo.png" width="32"> | [acme.sh](https://github.com/acmesh-official/acme.sh) | ACME client for SSL certificates |

### Supported Services

- **Collaboration**
  - Cryptpad - Encrypted document collaboration
  - LibreChat - Team chat platform

- **Media**
  - Emby - Media streaming server
  - PhotoPrism - Photo management
  - Radarr/Sonarr - Media management

- **Management & Utilities**
  - Portainer Agent - Container management
  - Home Assistant - Home automation
  - Actual Budget - Personal finance

## Get Started

### Prerequisites

- Docker Engine 24.0+
- Docker Compose v2
- Cloudflare DNS account
- Linux/Unix environment

### Quick Start

1. Clone and setup:
```bash
git clone https://github.com/yourusername/selfhosted.git
cd selfhosted
cp .env.example .env
```

2. Configure environment:
```bash
# Edit .env with your settings
nano .env
```

3. Initialize and start:
```bash
./selfhosted.sh init-certs  # Setup SSL certificates
./selfhosted.sh up         # Start enabled services
```

For detailed setup instructions, see our [Getting Started Guide](docs/getting-started.md). (WIP)

## Documentation

- [Roadmap](docs/roadmap.md)
- [Architecture Overview](docs/architecture.md) (WIP)
- [Service Configuration](docs/services.md) (WIP)
- [SSL Certificate Management](docs/ssl.md) (WIP)
- [Backup and Restore](docs/backup.md) (WIP)
- [Troubleshooting Guide](docs/troubleshooting.md) (WIP)

## Acknowledgements

- [khuedoan/homelab](https://github.com/khuedoan/homelab) - For README structure inspiration
- [nginx-proxy/nginx-proxy](https://github.com/nginx-proxy/nginx-proxy) - For reverse proxy concepts
- [acmesh-official/acme.sh](https://github.com/acmesh-official/acme.sh) - For SSL automation
