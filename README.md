# Homelab Docker Environment

A Docker-based homelab environment with automated reverse proxy, SSL certificate management, and service orchestration.

## Features

- Automated Nginx reverse proxy configuration
- Automatic SSL certificate management via acme.sh and Cloudflare DNS
- Dynamic service domain management
- Docker-based service orchestration
- Simple service enabling/disabling via .enabled-services file

## Supported Services

- **Collaboration**
  - Cryptpad (drive.domain.com)
  - LibreChat (chat.domain.com)

- **Media**
  - Emby (media server)
  - PhotoPrism (photo management)
  - Radarr (movie management)
  - Sonarr (TV show management)

- **Downloads**
  - Deluge (torrent client)
  - qBittorrent (torrent client)
  - Prowlarr (indexer management)

- **Management & Utilities**
  - Portainer Agent (container management)
  - Home Assistant (home automation)
  - Actual Budget (personal finance)

## Prerequisites

- Docker and Docker Compose v2
- Cloudflare DNS (for SSL certificates)
- Bash shell environment

## Quick Start

1. Clone and setup:
```bash
git clone https://github.com/yourusername/homelab.git
cd homelab
cp .env.example .env
```

2. Configure environment in `.env`:
```env
BASE_DOMAIN=yourdomain.com
WILDCARD_DOMAIN=*.yourdomain.com
CF_Token=your_cloudflare_token
CF_Account_ID=your_cloudflare_account_id
```

3. Enable desired services:
```bash
echo "cryptpad" > .enabled-services
echo "actual_budget" >> .enabled-services
```

4. Initialize SSL certificates:
```bash
./homelab.sh init-certs
```

5. Start services:
```bash
./homelab.sh up
```

## Usage

### Basic Commands

```bash
./homelab.sh up                  # Start all enabled services
./homelab.sh down               # Stop all services
./homelab.sh rebuild            # Rebuild all services
./homelab.sh list              # List available services
./homelab.sh dropin <service>   # Open shell in service container
./homelab.sh tail <service>     # View service logs
./homelab.sh init-certs        # Initialize SSL certificates
```

### Managing Services

1. Enable a service:
   - Add the service name to `.enabled-services`
   - Run `./homelab.sh rebuild`

2. Disable a service:
   - Remove the service from `.enabled-services`
   - Run `./homelab.sh rebuild`

## Directory Structure

```
.
├── docker-compose.yaml         # Main service definitions
├── homelab.sh                 # Main control script
├── .env                      # Environment configuration
├── .domains                  # Generated domain configurations
├── .enabled-services        # List of enabled services
├── scripts/
│   ├── build_domain.sh      # Domain configuration generator
│   └── setup_env.sh         # Environment setup
├── reverseproxy/
│   ├── templates/           # Nginx configuration templates
│   └── ssl/                # SSL certificates
└── tests/                  # BATS test files
```

## Development

### Testing

Tests are written using BATS (Bash Automated Testing System):

```bash
# Run all tests
bats tests/
```

### Pre-commit Hooks

The project uses pre-commit for code quality:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

Available hooks:
- Shell script linting (shellcheck)
- YAML validation
- Dockerfile linting
- Trailing whitespace cleanup
- BATS test running
- Secret detection

## Troubleshooting

1. SSL Certificate Issues:
   - Verify Cloudflare credentials in `.env`
   - Check `./homelab.sh init-certs` output
   - Verify domain DNS settings in Cloudflare

2. Service Access Issues:
   - Check service logs: `./homelab.sh tail <service>`
   - Verify service is enabled in `.enabled-services`
   - Check nginx configuration in reverseproxy/templates

3. Container Issues:
   - Access container shell: `./homelab.sh dropin <service>`
   - Check container status: `docker compose ps`
   - View container logs: `docker compose logs <service>`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests and pre-commit hooks
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
