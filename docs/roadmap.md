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

## Hardware Management
- [ ] Allow users to easily define their existing hardware
  - [ ] Easily add or remove hardware
  - [ ] Setup deployment infrastructure of choice
    - [ ] Docker (Compose and Swarm)
    - [ ] Kubernetes
- [ ] Infrastructure as code to deploy deployment infrastructure

## Homelab Applications
- [ ] Enable ML platforms
  - MLflow
  - Kubeflow
- [ ] Enable orchestration tools
  - Flye
  - Airflow
  - Dagster
  - Metaflow
- [ ] Enable CI/CD
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
- [ ] Enable reverse proxy
  - Nginx
- [ ] Enable DNS services
  - PiHole
- [ ] Enable VPN services
  - WireGuard
  - Tailscale

## Data Management
- [ ] Enable centralized storage
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
