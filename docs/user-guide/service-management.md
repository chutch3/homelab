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
task ansible:deploy:full

# Deploy only a specific service
task ansible:deploy:stack -- -e "stack_name=homepage"
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
# Update a service (redeploy with latest configuration)
task ansible:deploy:stack -- -e "stack_name=homepage"

# Remove a service stack
task ansible:teardown:stack -- -e "stack_name=homepage"

# Remove a service and its data volumes (add remove_volumes=true)
task ansible:teardown:stack -- -e "stack_name=homepage remove_volumes=true"
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
           - "traefik.http.routers.myservice.tls.certresolver=letsencrypt"
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
   task ansible:deploy:stack -- -e "stack_name=myservice"
   ```

## Remove a Service

1. **Remove from Docker Swarm**:
   ```bash
   task ansible:teardown:stack -- -e "stack_name=servicename"
   ```

2. **Clean up data volumes** (optional - destroys all data):
   ```bash
   # Add remove_volumes=true to the teardown command
   task ansible:teardown:stack -- -e "stack_name=servicename remove_volumes=true"
   ```

3. **Delete the compose file** (optional):
   ```bash
   rm -rf stacks/apps/servicename/
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
# Check service logs
docker service logs stackname_servicename --tail 50

# Check service status
docker service ps stackname_servicename
```

**Need to restart/update a service?**
```bash
# Redeploy with same configuration
docker stack deploy -c stacks/apps/servicename/docker-compose.yml servicename

# Force update (pulls latest image)
docker service update --image newimage:tag stackname_servicename
```

**Want to see what's running?**
```bash
# List all stacks
docker stack ls

# List services in a stack
docker stack services stackname

# List all running services
docker service ls

# See tasks/containers for a stack
docker stack ps stackname
```
