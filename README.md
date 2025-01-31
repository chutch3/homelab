# Dynamic Reverse Proxy with Docker

A dynamic reverse proxy setup using Nginx and Docker Compose that allows enabling/disabling services on demand. The system automatically manages both the Nginx configuration and Docker containers for each service.

## Features

- Dynamic enabling/disabling of services without container rebuilds
- Automatic SSL/HTTPS support with optional enabling/disabling
- Service grouping (media, torrents, etc.)
- Automatic container management based on enabled services
- Environment-based domain configuration
- WebSocket support for compatible services

## Prerequisites

- Docker (20.10.0+)
- Docker Compose (2.0.0+)
- Bash shell
- SSL certificates (for HTTPS support)
  - Valid SSL certificate in PEM format
  - Private key in PEM format
  - Root CA certificate (if using self-signed certificates)
  - Certificates should match your domain structure

## Directory Structure

```
.
├── docker-compose.yaml     # Main compose file for all services
├── .env                   # Environment configuration
├── reverseproxy/
│   ├── conf.d/
│   │   ├── available/    # Available service configurations
│   │   └── enabled/      # Symlinks to enabled configurations
│   ├── includes/         # Shared Nginx configuration
│   └── scripts/          # Management scripts
├── services/             # Service-specific configurations
└── ssl/                  # SSL certificates
```

## Configuration

1. Create a `.env` file with your domain configurations:

```env
# Base domain
BASE_DOMAIN=lab.local

# Service domains
DOMAIN_EMBY=emby.${BASE_DOMAIN}
DOMAIN_PHOTOPRISM=photo.${BASE_DOMAIN}
DOMAIN_PORTAINER=agent.${BASE_DOMAIN}
DOMAIN_HOMEASSISTANT=ha.${BASE_DOMAIN}
DOMAIN_BUDGET=budget.${BASE_DOMAIN}
DOMAIN_LIBRECHAT=chat.${BASE_DOMAIN}
DOMAIN_RADARR=radarr.${BASE_DOMAIN}
DOMAIN_DELUGE=deluge.${BASE_DOMAIN}
DOMAIN_PROWLARR=prowlarr.${BASE_DOMAIN}
DOMAIN_SONARR=sonarr.${BASE_DOMAIN}
DOMAIN_QBITTORRENT=qbittorrent.${BASE_DOMAIN}
```

2. Place your SSL certificates in the cert directory:
- `ca.pem` -> Root CA certificate
- `client.pem` -> SSL certificate
- `client.key` -> SSL private key

## Usage

### Basic Commands

All commands should be run using the homelab.sh script:

Start all enabled services:
```bash
homelab.sh start
```

Stop all services:
```bash
homelab.sh stop
```

Enable a service:
```bash
homelab.sh enable service.conf
```

Disable a service:
```bash
homelab.sh disable service.conf
```

### Adding New Services

1. Create a new configuration in `reverseproxy/conf.d/available/`:
```nginx
server {
    listen 80;
    server_name ${DOMAIN_NEWSERVICE};

    location / {
        include /etc/nginx/includes/proxy.conf;
        proxy_pass http://newservice:port;
    }

    access_log off;
    error_log  /var/log/nginx/error.log error;
}
```

2. Add the service to docker-compose.yaml with appropriate profile:
```yaml
services:
  newservice:
    image: newservice:latest
    profiles:
      - newservice
    restart: unless-stopped
    networks:
      - proxy
    environment:
      - TZ=UTC
    # ... other configuration ...
```

3. Update the .env file with the new service domain:
```env
DOMAIN_NEWSERVICE=newservice.${BASE_DOMAIN}
```

4. Enable the service:
```bash
homelab.sh enable newservice.conf
```

## SSL/HTTPS Support

SSL support can be toggled dynamically. When enabled:
- HTTP services will redirect to HTTPS
- HTTPS-only services will become available
- SSL configuration from includes/ssl.conf will be used

## Troubleshooting

1. Exec into container
```bash
homelab.sh dropin reverseproxy
```

2. View Nginx logs:
```bash
homelab.sh tail reverseproxy
```

3. Common issues:
- Domain not resolving: Check your .env file and DNS settings
- SSL not working: Verify certificates and ssl enabled flag
- Service unreachable: Ensure the service container is running

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
