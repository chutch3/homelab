# Service Management

## Deploy

```bash
task ansible:deploy                                          # Everything
task ansible:deploy:quick                                    # Apps only (skip infra)
task ansible:deploy:stack -- -e "stack_name=homepage"        # Single service
task ansible:deploy:services -- -e "only_apps=cicd,forgejo"  # Subset only
task ansible:deploy:services -- -e "skip_apps=sonarr,radarr" # Exclude specific
```

## Status

```bash
docker stack ls                                    # List deployed stacks
docker stack services homepage                     # Services in a stack
docker service logs homepage_homepage --tail 50 -f # Logs
docker service ps homepage_homepage                # Task placement/errors
```

## Remove

```bash
task ansible:teardown:stack -- -e "stack_name=homepage"                       # Keep volumes
task ansible:teardown:stack -- -e "stack_name=homepage remove_volumes=true"   # Delete data
```

---

## Add a New Service

```bash
mkdir stacks/apps/myservice
```

```yaml
# stacks/apps/myservice/docker-compose.yml
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
        - "traefik.swarm.network=traefik-public"

networks:
  traefik-public:
    external: true

volumes:
  myservice_data:
    driver: local
```

```bash
task ansible:deploy:stack -- -e "stack_name=myservice"
```

---

## Storage Provisioning

### iSCSI (databases, configs)

```bash
sudo mkdir -p /mnt/iscsi/app-data/myservice
sudo chown -R 1000:1000 /mnt/iscsi/app-data/myservice

# PostgreSQL needs UID 999
sudo chown -R 999:999 /mnt/iscsi/app-data/myservice/postgresql
```

### CIFS (media, bulk files)

Create the share on your NAS. The deployment creates the Docker volume automatically using `.env` credentials.

```yaml
volumes:
  myservice_media:
    driver: local
    driver_opts:
      type: "cifs"
      o: "username=${SMB_USERNAME},password=${SMB_PASSWORD},vers=3.0"
      device: "//${NAS_SERVER}/myservice"
```

---

## Cluster Operations

```bash
task ansible:cluster:sync           # Re-join nodes with changed IPs
task ansible:cluster:update-labels  # Apply inventory label changes to live swarm
task ansible:volume:ls              # List all Docker volumes
task ansible:volume:cleanup -- -e "stack_name=sonarr"  # Remove stale CIFS volumes
```
