# System Architecture

A simple overview of how the homelab platform works.

## How It Works

The platform deploys Docker containers using Docker Swarm across one or more machines:

```
.env file → Docker Swarm → Running Services
```

## Key Components

### Configuration
- **`.env`** - Your domain, Cloudflare credentials, and passwords
- **`machines.yaml`** - List of your servers (optional for single machine)

### Services
- **`stacks/apps/`** - Each folder contains a Docker Compose file for one service
- **`stacks/reverse-proxy/`** - Traefik handles SSL certificates and routing
- **`stacks/dns/`** - Local DNS server for internal resolution

### Storage
Services store data on your NAS via SMB/CIFS network shares (configured in `.env`).

## Deployment Process

When you run `./selfhosted.sh deploy`:

1. Sets up Docker Swarm cluster across your machines
2. Deploys infrastructure (DNS, Traefik proxy, monitoring)
3. Deploys all application services in parallel
4. Traefik automatically gets SSL certificates from Let's Encrypt

## Adding Services

To add a new service:

1. Create `stacks/apps/myservice/docker-compose.yml`
2. Include Traefik labels for routing
3. Run `./selfhosted.sh deploy` to deploy it

## Removing Services

To remove a service:

1. Delete the `stacks/apps/servicename/` folder
2. Run `./selfhosted.sh nuke servicename` to clean up data

That's it! The system handles the rest automatically.
