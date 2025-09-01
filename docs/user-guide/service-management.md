# Service Management

How to add, remove, and manage services in your homelab.

## View Available Services

```bash
# See what services are available
ls stacks/apps/

# See which have compose files (ready to deploy)
ls stacks/apps/*/docker-compose.yml
```

## Deploy Services

```bash
# Deploy all services
./selfhosted.sh deploy

# Deploy only specific services
./selfhosted.sh deploy --only-apps homepage,actual_server,homeassistant

# Deploy everything except heavy services
./selfhosted.sh deploy --skip-apps photoprism,emby
```

## Check Service Status

```bash
# List deployed stacks
docker stack ls

# Show services in a stack
docker stack services homepage

# View service logs
docker service logs homepage_homepage --tail 50 --follow
```

## Manage Individual Services

```bash
# Redeploy a service (keeps data)
./selfhosted.sh redeploy-service homepage

# Remove a service and its data
./selfhosted.sh nuke actual_server
```

## Add a New Service

1. **Create compose file**:
   ```bash
   mkdir stacks/apps/myservice
   nano stacks/apps/myservice/docker-compose.yml
   ```

2. **Basic service template**:
   ```yaml
   version: "3.9"

   services:
     myservice:
       image: myapp:latest
       volumes:
         - myservice_data:/data
       networks:
         - traefik-public
       deploy:
         labels:
           - "traefik.enable=true"
           - "traefik.http.routers.myservice.rule=Host(`myapp.${BASE_DOMAIN}`)"
           - "traefik.http.routers.myservice.entrypoints=websecure"
           - "traefik.http.routers.myservice.tls.certresolver=dns"
           - "traefik.http.services.myservice.loadbalancer.server.port=8080"

   networks:
     traefik-public:
       external: true

   volumes:
     myservice_data:
       driver: local
   ```

3. **Deploy it**:
   ```bash
   ./selfhosted.sh deploy --only-apps myservice
   ```

## Remove a Service

1. **Delete the compose file**:
   ```bash
   rm -rf stacks/apps/servicename/
   ```

2. **Clean up data** (optional):
   ```bash
   ./selfhosted.sh nuke servicename
   ```

## Environment Variables

Services use variables from your `.env` file:

- `${BASE_DOMAIN}` - Your domain name
- `${SMB_USERNAME}` - NAS username
- `${SMB_PASSWORD}` - NAS password
- `${NAS_SERVER}` - NAS hostname

Add new variables to `.env` and reference them in your compose files.

## Network Storage

To use NAS storage for a service:

```yaml
volumes:
  myservice_data:
    driver: local
    driver_opts:
      type: "cifs"
      o: "username=${SMB_USERNAME},password=${SMB_PASSWORD},vers=3.0"
      device: "//${NAS_SERVER}/myservice"
```

## Troubleshooting

**Service won't start?**
```bash
docker service logs stackname_servicename --tail 50
```

**Need to restart a service?**
```bash
./selfhosted.sh redeploy-service servicename
```

**Want to see what's running?**
```bash
docker service ls
docker stack ps stackname
```
