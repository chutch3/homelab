# DNS Configuration Playbooks

Incremental playbooks for configuring Technitium DNS Server with your homelab services.

## Testing Step-by-Step

These playbooks are designed to be tested incrementally, one step at a time, to ensure each piece works before moving to the next.

### Prerequisites

1. **Deploy DNS stack first:**
   ```bash
   task ansible:deploy:stack -- -e "stack_name=dns"
   # or via existing deployment
   ./homelab deploy --only-apps dns
   ```

2. **Set environment variables:**
   ```bash
   export BASE_DOMAIN="diyhub.dev"          # Your domain
   export DNS_ADMIN_PASSWORD="CHANGE_ME"     # DNS admin password
   ```

3. **Ensure Ansible inventory is configured:**
   - `ansible/inventory/02-hosts.yml` should have your machines with IPs

### Step 1: Test Authentication

**What it does:** Connects to DNS server, authenticates, gets API token

**Command:**
```bash
task ansible:dns:test-auth
```

**Expected output:**
```
✓ DNS API is responding on http://192.168.68.105:5380
✓ Successfully authenticated with DNS server
✓ Token received: YOUR_TOKEN_HERE
```

**Troubleshooting:**
- If connection fails: Check DNS container is running (`docker service ls`)
- If auth fails: Verify DNS_ADMIN_PASSWORD matches container password
- If timeout: Check firewall allows port 5380

### Step 2: Create Zone

**What it does:** Creates the primary DNS zone (e.g., diyhub.dev)

**Command:**
```bash
task ansible:dns:create-zone
```

**Expected output:**
```
✓ Created: diyhub.dev
Available zones: diyhub.dev
```

**Verify:**
- Login to DNS UI: `http://<manager-ip>:5380`
- Should see your zone listed

**Troubleshooting:**
- If "already exists": That's fine, playbook is idempotent
- If zone creation fails: Check BASE_DOMAIN is a valid domain

### Step 3: Add Machine A Records

**What it does:** Creates A records mapping machine hostnames → IPs

**Command:**
```bash
task ansible:dns:add-machines
```

**Expected output:**
```
✓ Created A records for machines:
  - giant.diyhub.dev → 192.168.68.105
  - imac.diyhub.dev  → 192.168.68.106
  - mini.diyhub.dev  → 192.168.68.107
```

**Verify:**
```bash
# Test DNS resolution (replace with your manager IP)
dig giant.diyhub.dev @192.168.68.105
dig imac.diyhub.dev @192.168.68.105

# Should return correct IPs
```

**Troubleshooting:**
- Records not created: Check inventory has correct ansible_host IPs
- Wrong IPs: Verify inventory/02-hosts.yml has accurate machine IPs

### Step 4: Discover Services

**What it does:** Scans docker-compose files for Traefik Host() labels

**Command:**
```bash
task ansible:dns:discover
```

**Expected output:**
```
✓ Discovered 11 service domain(s):
  - sonarr.diyhub.dev
  - radarr.diyhub.dev
  - jellyfin.diyhub.dev
  - homepage.diyhub.dev
  ...
```

**Verify:**
```bash
# Check discovered domains file
cat /tmp/discovered-domains.txt
```

**Troubleshooting:**
- No services found: Check stacks/ directory has docker-compose.yml files
- Missing services: Verify compose files have traefik.http.routers labels
- Pattern: Must match `Host(\`service.${BASE_DOMAIN}\`)`

### Step 5: Add Service CNAME Records

**What it does:** Creates CNAME records pointing services → manager hostname

**Command:**
```bash
task ansible:dns:add-services
```

**Expected output:**
```
✓ Created CNAME records for services:
  - sonarr.diyhub.dev → giant.diyhub.dev
  - radarr.diyhub.dev → giant.diyhub.dev
  ...
```

**Verify:**
```bash
# Test service DNS resolution
dig sonarr.diyhub.dev @192.168.68.105
dig radarr.diyhub.dev @192.168.68.105

# Should return CNAME → manager hostname → manager IP
```

**Troubleshooting:**
- CNAMEs not resolving: Ensure Step 3 completed (A records exist)
- Wrong target: Check groups['managers'][0] in inventory is correct

### Complete: Run All Steps

Once you've tested each step individually, run the complete playbook:

**Command:**
```bash
task ansible:dns:configure
```

**What it does:** Runs all steps in sequence (auth → zone → machines → services)

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ DNS Configuration Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Zone: diyhub.dev
DNS Server: http://192.168.68.105:5380

Records created:
  - Machine A records: 3
  - Service CNAME records: 10
  - Total records: 15

Access DNS admin panel:
  http://dns.diyhub.dev
  Username: admin
```

## Integration with Deployment

After DNS is working, integrate into your deployment workflow:

```bash
# Full deployment with DNS
task ansible:bootstrap           # Install Docker, etc.
task ansible:cluster:init        # Initialize swarm
task ansible:deploy:infra        # Deploy Traefik + DNS
sleep 30                         # Wait for DNS to be ready
task ansible:dns:configure       # Configure DNS records
task ansible:deploy              # Deploy app stacks
```

## Idempotency

All playbooks are idempotent and can be run multiple times safely:
- Creating existing zone: No change
- Adding existing A record: No change (or update if IP changed)
- Adding existing CNAME: Overwrites (useful for updates)

## Troubleshooting

### DNS Container Not Running
```bash
# Check DNS service
docker service ls | grep dns

# Check service logs
docker service logs <dns-service-name>
```

### Can't Reach DNS API
```bash
# Test API endpoint
curl http://<manager-ip>:5380/api/user/login

# Check firewall
sudo ufw status
```

### Records Not Resolving
```bash
# Use DNS server directly
dig @<dns-server-ip> <domain>

# Compare with your system DNS
dig <domain>

# Check DNS server has records
# Login to UI and verify records exist
```

### Service Discovery Missing Services
```bash
# Manually test the grep pattern
grep -r "traefik.http.routers" stacks/ | grep "Host("

# Check compose file format
cat stacks/apps/sonarr/docker-compose.yml | grep -A5 "traefik"
```

### Docker Service Names in Private DNS Logs

**Symptom:** Private DNS logs show repeated NxDomain queries for Docker service names (mariadb, immich-postgres, etc.) from IP addresses in the 10.0.0.0/8 range.

**Root Cause:** Docker's embedded DNS (127.0.0.11) forwards unresolved queries to external DNS servers when it can't resolve internal service names. This typically indicates a failing or non-existent Docker service.

**How to identify:**
```bash
# Check for services with 0 replicas (failing/crash-looping)
docker service ls | awk '$4 ~ /0\/[0-9]/ {print $2, $4}'

# Check why the service is failing
docker service ps <service-name> --no-trunc
```

**Fix:** Resolve the issue with the failing container, or scale down the application if it's not needed:
```bash
# Scale down to stop the failed service
docker service scale <service-name>=0
```

## Next Steps

Once DNS is configured:
1. Update your local DNS settings to use the homelab DNS server
2. Test accessing services: `http://sonarr.diyhub.dev`
3. Services should route through Traefik automatically
4. Re-run `task ansible:dns:configure` when adding new services
