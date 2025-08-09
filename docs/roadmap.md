# Mission

The mission of self-hosted is to:

- Use existing hardware
- Get up and running fast
- Enable data sovereignty and control
- Enable easy customization where needed
- Connect open source projects together
- Support multiple application domains (home media, homelab, privacy, smart home, etc.)
- Documentation and guides for getting started

# Roadmap to v1.0

This is a list of high level goals and tasks to achieve the mission.

## ✅ Core Platform (COMPLETED)

### Configuration & Deployment
- [x] **Unified Configuration System** - Single `config/services.yaml` source of truth
- [x] **Multi-Platform Deployment** - Docker Compose, Docker Swarm, Kubernetes support
- [x] **Automatic File Generation** - Creates deployment files, nginx configs, domain variables
- [x] **Enhanced CLI Interface** - Modern command structure with helpful output
- [x] **Service Dependency Resolution** - Intelligent startup ordering and circular dependency detection
- [x] **Volume Management** - Local and NFS storage support with centralized configuration
- [x] **Domain Standardization** - Consistent naming, validation, and SSL automation
- [x] **Comprehensive Testing** - 152 tests with 95%+ pass rate, TDD methodology
- [x] **CI/CD Pipeline** - GitHub Actions with automated testing, linting, semantic releases

### Infrastructure Management
- [x] **Docker Infrastructure** - Full Compose and Swarm support
- [x] **Kubernetes Foundation** - Unified config generation for K8s manifests
- [x] **Machine Configuration** - YAML-based hardware definition and SSH management
- [x] **SSL Automation** - Cloudflare DNS + acme.sh integration
- [x] **Reverse Proxy** - Dynamic nginx configuration with SSL termination

## 🔄 Current Phase: Production Readiness

### Integration & Polish
- [ ] End-to-end integration testing
- [ ] Real-world deployment validation
- [ ] Performance optimization and monitoring
- [ ] User documentation and migration guides

## Hardware Management
- [x] Allow users to easily define their existing hardware (`machines.yml`)
  - [x] Easily add or remove hardware
  - [x] Setup deployment infrastructure of choice
    - [x] Docker (Compose and Swarm)
    - [x] Kubernetes (unified config generation)
- [x] Infrastructure as code to deploy deployment infrastructure

## Homelab Applications
- [ ] Enable ML platforms
  - MLflow
  - Kubeflow
- [ ] Enable orchestration tools
  - Flye
  - Airflow
  - Dagster
  - Metaflow
- [x] **Enable CI/CD** - ✅ **COMPLETED**
  - [x] GitHub Actions workflows for PR validation and releases
  - [x] Automated linting (ShellCheck, yamllint, hadolint, gitleaks)
  - [x] Comprehensive test suite integration (152 BATS tests)
  - [x] Semantic versioning with conventional commits
  - [x] Automated changelog generation and GitHub releases
  - [x] Taskfile integration for local/CI command consistency
- [ ] Enable data & cache services
  - PostgreSQL
  - Redis
- [ ] Enable queue services
  - RabbitMQ
  - Kafka
- [ ] Enable monitoring
  - Prometheus
  - Grafana
- [ ] Enable logging
  - Loki
- [ ] Enable geospatial
  - PostGIS

## Home Media
- [ ] Enable media servers
  - Plex
  - Jellyfin
  - Emby
  - Sonarr
  - Radarr
- [ ] Enable photo servers
  - PhotoPrism
- [ ] Enable torrent services
  - qBittorrent

## Privacy Applications
- [ ] Enable email services
  - Inbound (Mailu)
  - Outbound (SMTP2Go)
- [ ] Enable drive & docs
  - CryptPad
- [ ] Enable calendar services
  - CalDAV
- [ ] Enable contact management
  - CardDAV
- [ ] Enable note taking
  - Joplin
- [ ] Enable password management
  - Bitwarden

## Smart Home
- [ ] Enable home automation
  - Home Assistant

## Access & Security
- [x] **Enable reverse proxy** - ✅ **COMPLETED**
  - [x] Nginx with automatic configuration generation
  - [x] SSL termination and certificate management
  - [x] Dynamic upstream configuration from services.yaml
- [ ] Enable DNS services
  - PiHole
- [ ] Enable VPN services
  - WireGuard
  - Tailscale

## Data Management
- [x] **Enable centralized storage** - ✅ **COMPLETED**
  - [x] Volume management with local and NFS support
  - [x] Centralized configuration in `config/volumes.yaml`
  - [x] Automatic volume path generation and directory creation
  - [x] Backup priority configuration and script generation
- [ ] Enable private cloud storage
  - Syncthing
- [ ] Enable backup solutions
  - Rsync
  - Backblaze

## Customization
- [ ] Enable application-specific configurations
- [ ] Enable hardware-specific configurations
- [ ] Enable user-specific configurations

## Documentation
- [ ] Create comprehensive guides for getting started
