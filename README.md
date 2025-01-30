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

## Directory Structure


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

2. Place your SSL certificates:
- `rootCA.pem` -> Root CA certificate
- `_wildcard.lab.local.pem` -> SSL certificate
- `_wildcard.lab.local-key.pem` -> SSL private key

## Usage

### Basic Commands

Start all enabled services:
```bash
./reverseproxy/scripts/startup.sh start
```

Stop all services:
```bash
./reverseproxy/scripts/startup.sh stop
```

Enable a service:
```bash
./reverseproxy/scripts/startup.sh enable emby.conf
```

Disable a service:
```bash
./reverseproxy/scripts/startup.sh disable emby.conf
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
    # ... other configuration ...
```

3. Update the startup script to handle the new service
4. Add the domain to your .env file

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

