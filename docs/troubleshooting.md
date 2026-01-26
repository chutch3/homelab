# Troubleshooting

Common issues and solutions for your homelab deployment. This guide covers the most frequently encountered problems across different service categories.

## Table of Contents

1. [OCFS2 Cluster - IP Address Changes](#ocfs2-cluster-ip-address-changes)
2. [Service Deployment Failures](#service-deployment-failures)
3. [SSL Certificate Issues](#ssl-certificate-issues)
4. [DNS Resolution Problems](#dns-resolution-problems)
5. [Docker Swarm Networking](#docker-swarm-networking)
6. [Authentik SSO Integration](#authentik-sso-integration)
7. [Storage Mount Failures](#storage-mount-failures)
8. [Database Performance Issues](#database-performance-issues)

---

## OCFS2 Cluster - IP Address Changes

**Issue:** After a network change, nodes with new IP addresses fail to mount OCFS2 filesystems with error `-107` (ENOTCONN) in `ocfs2_dlm_init`.

**Symptoms:**
```
o2net: Connection to node <name> shutdown, state 7
o2net: No connection established with node X after 30.0 seconds
o2cb: This node could not connect to nodes
(mount.ocfs2): ERROR: status = -107
```

**Root Cause:** O2CB cluster caches node IP addresses in kernel state (`/sys/kernel/config/cluster/homelab/node/*/ipv4_address`). When node IP addresses change, the kernel state becomes stale and O2NET connections fail during handshake.

**Solution:**

1. **Remove affected nodes from cluster:**
   ```bash
   # On all nodes
   /usr/sbin/o2cb remove-node homelab <node-name>
   ```

2. **Stop O2CB on all nodes:**
   ```bash
   systemctl stop o2cb
   ```

3. **Re-add nodes with new IPs:**
   ```bash
   # On all nodes
   /usr/sbin/o2cb add-node homelab <node-name> --ip <new-ip> --port 7777 --number <node-number>
   ```

4. **Restart O2CB:**
   ```bash
   systemctl restart o2cb
   ```

5. **If kernel state persists:** Reboot nodes that still show old IPs in `/sys/kernel/config/cluster/homelab/node/*/ipv4_address`.

**Prevention:** After IP address changes, reboot all cluster nodes to ensure clean O2CB registration with new IPs.

---

## Service Deployment Failures

**Issue:** Docker stack fails to deploy, or services restart repeatedly after deployment.

### Stack Fails to Deploy

**Symptoms:**
```
Creating service myapp_service
failed to create service myapp_service: Error response from daemon: ...
```

**Common Causes:**
- Missing environment variables in `.env` file
- Invalid Docker Compose syntax
- Missing Docker secrets
- Network not created
- Node constraints not met (labels missing)

**Solution:**

1. **Verify environment variables:**
   ```bash
   # Check if all required variables are set
   grep -v '^#' .env | grep -v '^$'
   ```

2. **Validate Docker Compose syntax:**
   ```bash
   cd stacks/apps/myservice
   docker compose config
   ```

3. **Check Docker secrets:**
   ```bash
   docker secret ls
   # Create missing secrets
   echo "secret-value" | docker secret create secret_name -
   ```

4. **Verify network exists:**
   ```bash
   docker network ls | grep traefik-public
   # Create if missing
   docker network create --driver overlay traefik-public
   ```

5. **Check node labels:**
   ```bash
   docker node ls
   docker node inspect <node-name> --format '{{.Spec.Labels}}'
   # Add missing labels
   docker node update --label-add database=true <node-name>
   ```

### Container Restarts Repeatedly

**Symptoms:**
```bash
docker service ps myapp_service
# Shows multiple restarts
```

**Common Causes:**
- Application configuration errors
- Missing volume mounts
- Database connection failures
- Port conflicts
- Health check failures

**Solution:**

1. **Check service logs:**
   ```bash
   docker service logs myapp_service --tail 100 --follow
   ```

2. **Inspect service tasks:**
   ```bash
   docker service ps myapp_service --no-trunc
   ```

3. **Verify volume mounts:**
   ```bash
   # Check if mount points exist
   ls -la /mnt/iscsi/app-data/myapp
   ls -la /mnt/cifs/
   ```

4. **Check port conflicts:**
   ```bash
   docker service inspect myapp_service --format '{{.Endpoint.Ports}}'
   netstat -tulpn | grep <port>
   ```

5. **Test database connectivity:**
   ```bash
   docker exec -it $(docker ps -q -f name=myapp) sh
   # Inside container, test connection
   nc -zv database-host 5432
   ```

### Health Check Failures

**Symptoms:**
Service shows as running but marked unhealthy in `docker service ps`.

**Solution:**

1. **Check health check configuration in docker-compose.yml:**
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

2. **Test health check manually:**
   ```bash
   docker exec -it $(docker ps -q -f name=myapp) curl -f http://localhost:3000/health
   ```

3. **Increase timeout or retries** if service is slow to start

**Prevention:**
- Always validate compose files with `docker compose config` before deployment
- Test services locally before deploying to swarm
- Use `docker service logs` immediately after deployment to catch early errors

---

## SSL Certificate Issues

**Issue:** HTTPS not working, certificate not issued, or Cloudflare DNS challenges failing.

### Certificate Not Issued

**Symptoms:**
- Service accessible via HTTP but not HTTPS
- Browser shows "connection not secure"
- Traefik dashboard shows no certificate

**Common Causes:**
- Cloudflare API token invalid or expired
- DNS records not pointing to server
- Let's Encrypt rate limits hit
- Traefik not configured for certificate resolver

**Solution:**

1. **Check Traefik logs:**
   ```bash
   docker service logs traefik_traefik --tail 100 --follow
   # Look for ACME challenge errors
   ```

2. **Verify Cloudflare API token:**
   ```bash
   # Check token in .env file
   grep CLOUDFLARE_DNS_API_TOKEN .env

   # Test token with Cloudflare API
   curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
        -H "Authorization: Bearer $CLOUDFLARE_DNS_API_TOKEN"
   ```

3. **Verify DNS records:**
   ```bash
   dig yourdomain.com
   dig subdomain.yourdomain.com
   # Should point to your server IP
   ```

4. **Check acme.json file:**
   ```bash
   ls -la /mnt/iscsi/app-data/traefik/acme.json
   # Should have 600 permissions
   chmod 600 /mnt/iscsi/app-data/traefik/acme.json
   ```

5. **Check Traefik labels on service:**
   ```yaml
   labels:
     - traefik.enable=true
     - traefik.http.routers.myservice.rule=Host(`myapp.${BASE_DOMAIN}`)
     - traefik.http.routers.myservice.tls=true
     - traefik.http.routers.myservice.tls.certresolver=letsencrypt
   ```

### Certificate Expired or Invalid

**Symptoms:**
- Browser shows certificate error
- Certificate expiry warning

**Solution:**

1. **Force certificate renewal:**
   ```bash
   # Remove old certificate from acme.json
   # Traefik will automatically request a new one
   docker service update --force traefik_traefik
   ```

2. **Check Let's Encrypt rate limits:**
   - Limit: 50 certificates per week per domain
   - Use staging environment for testing

**Prevention:**
- Monitor certificate expiry with Uptime Kuma
- Ensure Cloudflare API token doesn't expire
- Use wildcard certificates to reduce certificate count
- Test with Let's Encrypt staging environment first

---

## DNS Resolution Problems

**Issue:** Services not accessible by domain name, or DNS server not responding.

### Services Not Accessible by Domain

**Symptoms:**
```bash
ping myapp.yourdomain.com
# ping: cannot resolve myapp.yourdomain.com: Unknown host
```

**Common Causes:**
- Technitium DNS not running
- DNS records not configured
- Client not using correct DNS server
- Firewall blocking DNS port 5380

**Solution:**

1. **Check Technitium DNS status:**
   ```bash
   docker service ls | grep dns
   docker service logs dns_dns --tail 50
   ```

2. **Verify DNS records in Technitium:**
   - Access Technitium UI: `http://<server-ip>:5380`
   - Check A records for your domain
   - Verify wildcard records (*.yourdomain.com)

3. **Test DNS resolution:**
   ```bash
   # Test with Technitium DNS
   dig @<server-ip> myapp.yourdomain.com

   # Test with system DNS
   dig myapp.yourdomain.com
   ```

4. **Check client DNS configuration:**
   ```bash
   # Linux
   cat /etc/resolv.conf
   # Should contain: nameserver <server-ip>

   # Update if needed
   echo "nameserver <server-ip>" | sudo tee /etc/resolv.conf
   ```

### DNS Server Not Responding

**Symptoms:**
```bash
dig @<server-ip> yourdomain.com
# ;; connection timed out; no servers could be reached
```

**Solution:**

1. **Check DNS service is running:**
   ```bash
   docker service ps dns_dns
   ```

2. **Verify port 53 is open:**
   ```bash
   sudo netstat -tulpn | grep :53
   # Should show docker-proxy listening
   ```

3. **Check firewall rules:**
   ```bash
   sudo ufw status
   sudo ufw allow 53/tcp
   sudo ufw allow 53/udp
   sudo ufw allow 5380/tcp
   ```

4. **Restart DNS service:**
   ```bash
   task ansible:deploy:stack -- -e "stack_name=dns"
   ```

**Prevention:**
- Configure DNS records before deploying services
- Use wildcard DNS records (*.yourdomain.com) for easier management
- Monitor DNS service with Uptime Kuma
- Document all DNS records

---

## Docker Swarm Networking

**Issue:** Overlay network issues, services can't communicate, or node connectivity problems.

### Services Can't Communicate

**Symptoms:**
- Service A cannot reach Service B
- Connection timeouts between containers
- Services on different nodes can't communicate

**Common Causes:**
- Services not on same overlay network
- Firewall blocking overlay network ports (4789/udp)
- Network encryption issues
- MTU size mismatch

**Solution:**

1. **Verify services are on same network:**
   ```bash
   docker service inspect myservice --format '{{.Spec.TaskTemplate.Networks}}'
   docker network ls
   docker network inspect traefik-public
   ```

2. **Check overlay network connectivity:**
   ```bash
   # From one service
   docker exec -it $(docker ps -q -f name=myapp) ping other-service
   ```

3. **Verify firewall rules allow overlay network:**
   ```bash
   # Port 4789/udp must be open between nodes
   sudo ufw allow 4789/udp
   sudo ufw allow 7946/tcp
   sudo ufw allow 7946/udp
   ```

4. **Check MTU size:**
   ```bash
   ip link show | grep mtu
   # All nodes should have same MTU
   ```

### Node Connectivity Problems

**Symptoms:**
```bash
docker node ls
# Shows nodes as "Down" or "Unreachable"
```

**Solution:**

1. **Check node availability:**
   ```bash
   docker node ls
   docker node inspect <node-name>
   ```

2. **Verify Swarm ports are open:**
   ```bash
   # Required ports between nodes
   sudo ufw allow 2377/tcp   # Cluster management
   sudo ufw allow 7946/tcp   # Node communication
   sudo ufw allow 7946/udp   # Node communication
   sudo ufw allow 4789/udp   # Overlay network
   ```

3. **Check node connectivity:**
   ```bash
   # From manager node
   ping <worker-node-ip>
   nc -zv <worker-node-ip> 2377
   ```

4. **Rejoin node to swarm if needed:**
   ```bash
   # On worker node
   docker swarm leave

   # On manager node, get join token
   docker swarm join-token worker

   # On worker node, rejoin with token
   docker swarm join --token <token> <manager-ip>:2377
   ```

### Network Not Found

**Symptoms:**
```
Error response from daemon: network traefik-public not found
```

**Solution:**

1. **Create missing network:**
   ```bash
   docker network create \
     --driver overlay \
     --attachable \
     traefik-public
   ```

2. **Verify network exists:**
   ```bash
   docker network ls | grep traefik-public
   ```

**Prevention:**
- Document required firewall ports
- Use network monitoring to detect connectivity issues
- Keep Docker Engine updated on all nodes
- Regularly check node health with `docker node ls`

---

## Authentik SSO Integration

**Issue:** Forward auth not working, OAuth redirect errors, or LDAP authentication failures.

### Forward Auth Not Working

**Symptoms:**
- Accessing service shows "502 Bad Gateway"
- No SSO login prompt appears
- Traefik returns authentication errors

**Common Causes:**
- Authentik proxy outpost not running
- Middleware not configured correctly
- Authentik host URL incorrect
- Service not configured to use middleware

**Solution:**

1. **Verify Authentik services are running:**
   ```bash
   docker service ls | grep authentik
   # Should see: authentik_server, authentik_worker, authentik_proxy
   ```

2. **Check Authentik proxy outpost logs:**
   ```bash
   docker service logs authentik_proxy --tail 50 --follow
   ```

3. **Verify Traefik middleware configuration:**
   ```bash
   docker service inspect authentik_proxy --format '{{.Spec.Labels}}'
   # Should contain middleware labels
   ```

4. **Check service uses middleware:**
   ```yaml
   labels:
     - traefik.http.routers.myservice.middlewares=authentik@swarm
   ```

5. **Verify Authentik host URL:**
   ```bash
   # In authentik service environment
   grep AUTHENTIK_HOST stacks/apps/authentik/docker-compose.yml
   # Should match: https://auth.${BASE_DOMAIN}
   ```

### OAuth Redirect Errors

**Symptoms:**
- "Invalid redirect URI" error
- "OAuth callback failed"
- User redirected to wrong URL after login

**Solution:**

1. **Check OAuth provider configuration in Authentik:**
   - Login to Authentik: `https://auth.yourdomain.com`
   - Go to Applications → Providers
   - Verify redirect URIs match service callback URLs
   - Common format: `https://myapp.yourdomain.com/oauth/callback`

2. **Verify service OAuth configuration:**
   ```yaml
   environment:
     - OAUTH_ISSUER_URL=https://auth.${BASE_DOMAIN}/application/o/myapp/
     - OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}
     - OAUTH_CLIENT_SECRET=${OAUTH_CLIENT_SECRET}
   ```

3. **Check environment variables are set:**
   ```bash
   grep OAUTH .env
   ```

4. **Test OAuth flow:**
   - Clear browser cache and cookies
   - Try SSO login
   - Check browser developer console for errors

### LDAP Authentication Fails

**Symptoms:**
- Service shows "LDAP bind failed"
- Cannot authenticate with LDAP credentials
- Connection timeouts to LDAP server

**Solution:**

1. **Verify Authentik LDAP outpost is running:**
   ```bash
   docker service ls | grep authentik_ldap
   docker service logs authentik_ldap --tail 50
   ```

2. **Check LDAP port accessibility:**
   ```bash
   # Test LDAP connection
   nc -zv <authentik-host> 389
   nc -zv <authentik-host> 636  # LDAPS
   ```

3. **Verify service LDAP configuration:**
   ```yaml
   environment:
     - LDAP_HOST=authentik_ldap
     - LDAP_PORT=3389  # Internal Docker network
     - LDAP_BASE_DN=dc=ldap,dc=goauthentik,dc=io
   ```

4. **Test LDAP bind:**
   ```bash
   ldapsearch -x -H ldap://auth.yourdomain.com:389 \
     -D "cn=admin,dc=ldap,dc=goauthentik,dc=io" \
     -w <password> -b "dc=ldap,dc=goauthentik,dc=io"
   ```

**Prevention:**
- Document all OAuth redirect URIs
- Test SSO integration before deploying to production
- Use Authentik's application wizard for consistent configuration
- Monitor Authentik service health
- Keep Authentik outpost tokens secure and don't expire them

---

## Storage Mount Failures

**Issue:** CIFS/SMB mounts not working, iSCSI mount issues, or permission denied errors.

### CIFS/SMB Mounts Not Working

**Symptoms:**
```bash
ls /mnt/cifs/
# ls: cannot access '/mnt/cifs/': No such file or directory
```
Or:
```
docker service logs myapp
# Error: cannot access /media: Permission denied
```

**Common Causes:**
- NAS server not reachable
- Incorrect SMB credentials
- Mount point not created
- Network connectivity issues
- SMB version mismatch

**Solution:**

1. **Verify NAS is reachable:**
   ```bash
   ping ${NAS_SERVER}
   # Test SMB port
   nc -zv ${NAS_SERVER} 445
   ```

2. **Check mount configuration in docker-compose.yml:**
   ```yaml
   volumes:
     - type: bind
       source: /mnt/cifs/media
       target: /media
   ```

3. **Verify CIFS mount on host:**
   ```bash
   # Check if mounted
   mount | grep cifs
   df -h | grep cifs

   # Test manual mount
   sudo mount -t cifs //${NAS_SERVER}/share /mnt/cifs/media \
     -o username=${SMB_USERNAME},password=${SMB_PASSWORD},vers=3.0
   ```

4. **Check SMB credentials:**
   ```bash
   grep SMB .env
   # Verify username, password, and domain are correct
   ```

5. **Create mount points if missing:**
   ```bash
   sudo mkdir -p /mnt/cifs/media
   sudo chmod 755 /mnt/cifs
   ```

### iSCSI Mount Issues

**Symptoms:**
```bash
ls /mnt/iscsi/app-data
# ls: cannot access '/mnt/iscsi/app-data': Transport endpoint is not connected
```

**Solution:**

1. **Check iSCSI session:**
   ```bash
   sudo iscsiadm -m session
   # Should show active sessions
   ```

2. **Verify OCFS2 cluster status:**
   ```bash
   sudo o2cb cluster-status homelab
   # All nodes should show online
   ```

3. **Check mount status:**
   ```bash
   mount | grep ocfs2
   df -h | grep iscsi
   ```

4. **Restart iSCSI and OCFS2:**
   ```bash
   sudo systemctl restart o2cb
   sudo systemctl restart ocfs2
   sudo iscsiadm -m session --rescan
   ```

5. **Re-mount if needed:**
   ```bash
   sudo mount -a
   # Or specific mount
   sudo mount /mnt/iscsi/app-data
   ```

### Permission Denied Errors

**Symptoms:**
```
docker service logs myapp
# Error: cannot write to /data: Permission denied
```

**Solution:**

1. **Check file permissions on host:**
   ```bash
   ls -la /mnt/iscsi/app-data/myapp
   ls -la /mnt/cifs/media
   ```

2. **Verify UID/GID match:**
   ```bash
   # In docker-compose.yml
   environment:
     - PUID=1000
     - PGID=1000

   # Check ownership on host
   sudo chown -R 1000:1000 /mnt/iscsi/app-data/myapp
   ```

3. **For CIFS mounts, check mount options:**
   ```yaml
   volumes:
     - type: volume
       source: myapp_media
       target: /media
       volume:
         nocopy: true

   volumes:
     myapp_media:
       driver: local
       driver_opts:
         type: cifs
         o: "username=${SMB_USERNAME},password=${SMB_PASSWORD},uid=1000,gid=1000,file_mode=0770,dir_mode=0770"
         device: "//${NAS_SERVER}/media"
   ```

**Prevention:**
- Use Ansible to configure mounts consistently
- Document mount points and credentials
- Test mounts before deploying services
- Monitor mount health with automated checks
- Use consistent UID/GID across services (1000:1000)

---

## Database Performance Issues

**Issue:** Slow queries, connection timeouts, or performance degradation for database-heavy services (Immich, LibreChat).

### Slow Queries or Timeouts

**Symptoms:**
- Application shows "Database connection timeout"
- Web UI is extremely slow
- Services restart due to health check failures
- High CPU usage on database container

**Common Causes:**
- Database running on network storage (CIFS/SMB) instead of local storage
- Insufficient resources allocated to database
- Database not placed on correct node
- Database needs vacuuming or optimization

**Solution:**

1. **CRITICAL: Verify database is on local storage:**
   ```bash
   docker service inspect immich_postgres --format '{{.Spec.TaskTemplate.Placement}}'
   # Should show: map[Constraints:[node.labels.database==true]]

   # Check node label exists
   docker node inspect <node-name> --format '{{.Spec.Labels}}'
   ```

2. **Verify database volume is local, not network:**
   ```yaml
   # CORRECT: Local volume (no driver_opts for cifs)
   volumes:
     immich_postgres:
       # No driver or driver_opts = local storage

   # INCORRECT: CIFS mount (will be slow)
   volumes:
     immich_postgres:
       driver: local
       driver_opts:
         type: cifs
         device: "//${NAS_SERVER}/database"  # DON'T DO THIS
   ```

3. **Check database logs:**
   ```bash
   docker service logs immich_postgres --tail 100 --follow
   docker service logs librechat_mongodb --tail 100 --follow
   ```

4. **Monitor database resource usage:**
   ```bash
   docker stats $(docker ps -q -f name=postgres)
   docker stats $(docker ps -q -f name=mongodb)
   ```

5. **For PostgreSQL, vacuum database:**
   ```bash
   docker exec -it $(docker ps -q -f name=postgres) psql -U postgres -d immich
   # Inside psql
   VACUUM ANALYZE;
   \q
   ```

### Connection Errors

**Symptoms:**
```
Error: Connection to database failed
could not connect to server: Connection refused
```

**Solution:**

1. **Verify database service is running:**
   ```bash
   docker service ls | grep postgres
   docker service ls | grep mongodb
   docker service ps immich_postgres --no-trunc
   ```

2. **Check database credentials:**
   ```bash
   # In docker-compose.yml
   grep DB_PASSWORD stacks/apps/immich/docker-compose.yml
   grep DB_USERNAME stacks/apps/immich/docker-compose.yml

   # Verify in .env
   grep IMMICH_DB .env
   ```

3. **Test database connection from application container:**
   ```bash
   docker exec -it $(docker ps -q -f name=immich_server) sh
   # Inside container
   nc -zv immich_postgres 5432
   ```

4. **Check database is ready:**
   ```bash
   docker exec -it $(docker ps -q -f name=postgres) pg_isready -U postgres
   ```

### Performance Degradation Over Time

**Symptoms:**
- Application was fast but now slow
- Database size growing rapidly
- Disk I/O very high

**Solution:**

1. **Check database size:**
   ```bash
   # PostgreSQL
   docker exec -it $(docker ps -q -f name=postgres) psql -U postgres -d immich -c "SELECT pg_size_pretty(pg_database_size('immich'));"

   # MongoDB
   docker exec -it $(docker ps -q -f name=mongodb) mongo librechat --eval "db.stats()"
   ```

2. **Optimize PostgreSQL:**
   ```bash
   docker exec -it $(docker ps -q -f name=postgres) psql -U postgres -d immich
   # Inside psql
   VACUUM FULL ANALYZE;
   REINDEX DATABASE immich;
   ```

3. **Check disk space on database node:**
   ```bash
   df -h
   # Ensure sufficient free space
   ```

4. **Increase database resources if needed:**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G
       reservations:
         memory: 1G
   ```

**Prevention:**
- **ALWAYS run PostgreSQL and MongoDB on local storage, never network storage**
- Set node labels correctly: `docker node update --label-add database=true <node>`
- Use node with fast SSD for database workloads
- Monitor database size and performance with Prometheus/Grafana
- Schedule regular maintenance (VACUUM for PostgreSQL)
- Allocate sufficient resources for database containers
- Keep database versions updated

### Database Node Label Missing

**Symptoms:**
```
docker service ps immich_postgres
# Shows "no suitable node" error
```

**Solution:**

1. **Add database node label:**
   ```bash
   # List nodes
   docker node ls

   # Add label to node with fast local storage
   docker node update --label-add database=true <node-name>

   # Verify label
   docker node inspect <node-name> --format '{{.Spec.Labels}}'
   ```

2. **Redeploy service:**
   ```bash
   task ansible:deploy:stack -- -e "stack_name=immich"
   ```

**Critical Note:** For services like Immich and LibreChat with PostgreSQL or MongoDB databases, local storage is **mandatory** for acceptable performance. Network storage (CIFS/SMB) will result in extremely slow performance, connection timeouts, and health check failures.

---

## General Troubleshooting Tips

### Check Service Logs
```bash
# Follow logs in real-time
docker service logs <service-name> --tail 100 --follow

# Search logs for errors
docker service logs <service-name> --tail 1000 | grep -i error
```

### Inspect Service Configuration
```bash
# View service details
docker service inspect <service-name>

# View service tasks (replicas)
docker service ps <service-name> --no-trunc

# View service placement constraints
docker service inspect <service-name> --format '{{.Spec.TaskTemplate.Placement}}'
```

### Restart Service
```bash
# Restart single service
docker service update --force <service-name>

# Redeploy entire stack
task ansible:deploy:stack -- -e "stack_name=myapp"
```

### Check System Resources
```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Check Docker resources
docker system df
```

### Get Shell Access to Container
```bash
# Find container
docker ps | grep myapp

# Execute shell
docker exec -it <container-id> sh
# Or bash if available
docker exec -it <container-id> bash
```

## Need More Help?

If you're still experiencing issues:

1. **Check service-specific documentation** in `/stacks/apps/<service>/README.md`
2. **Review recent changes** with `git log`
3. **Search existing issues** on GitHub
4. **Create new issue** with detailed logs and configuration

[Report issues on GitHub →](https://github.com/chutch3/homelab/issues)
