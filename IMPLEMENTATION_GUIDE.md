# Homelab Ansible Refactor - Implementation Guide

**Date:** 2026-03-11
**Status:** Ready for testing
**Estimated Migration Time:** 2-4 hours

---

## Overview

This guide explains how to migrate from the current "messy" Ansible infrastructure to the refactored, production-grade version with full verification and proper module usage.

---

## What's Been Refactored

### ✅ Completed Components

1. **`ansible/requirements.yml`** - Updated with pinned versions + ansible.posix
2. **`ansible/roles/storage/`** - NEW role eliminating 427 lines of duplication
3. **`ansible/playbooks/cluster/teardown.yml`** - NEW scorched-earth teardown with verification
4. **`ansible/playbooks/cluster/init-refactored.yml`** - Swarm init with full verification
5. **`ansible/playbooks/cluster/join-refactored.yml`** - Worker join with full verification
6. **`ansible/roles/dns/tasks/add-service-cnames-refactored.yml`** - DNS with dig verification
7. **`ansible/roles/uptime_kuma/tasks/add-service-monitors-refactored.yml`** - Uptime Kuma with status verification

---

## Migration Strategy

### Phase 1: Install Updated Dependencies (5 minutes)

```bash
cd /home/cody/workspace/homelab/ansible

# Install updated collections
ansible-galaxy collection install -r requirements.yml --force

# Verify collections installed
ansible-galaxy collection list | grep -E "(community.docker|community.general|ansible.posix)"
```

**Expected Output:**
```
community.docker    3.4.x or higher
community.general   8.0.x or higher
ansible.posix       1.5.x or higher
lucasheld.uptime_kuma 1.2.x or higher
```

---

### Phase 2: Test New Storage Role (30 minutes)

The new storage role replaces the duplicated iSCSI logic in the common role.

#### 2.1 Update Bootstrap Playbook

Edit `ansible/playbooks/bootstrap.yml`:

```yaml
# OLD:
roles:
  - common  # Contains iSCSI setup
  - ssh
  - docker
  - cifs
  - gpu

# NEW:
roles:
  - common  # Now only base OS setup
  - ssh
  - docker
  - storage  # NEW: Handles iSCSI/OCFS2
  - cifs
  - gpu
```

#### 2.2 Update Common Role

Edit `ansible/roles/common/tasks/main.yml`:

**Remove lines 43-488** (all iSCSI/OCFS2 logic) - this is now in the storage role.

Keep only:
- apt cache update
- Install common packages
- Set timezone
- Ensure required directories exist

#### 2.3 Test Storage Role

```bash
# Dry run first
ansible-playbook playbooks/bootstrap.yml --check --diff -l workers

# Apply to one worker
ansible-playbook playbooks/bootstrap.yml -l giant

# Verify mounts
ansible workers -m command -a "mount | grep ocfs2"
ansible workers -m command -a "iscsiadm -m session"
```

---

### Phase 3: Test New Teardown Playbook (30 minutes)

#### 3.1 Deploy Test Stack

```bash
# Deploy a simple test stack
cd /home/cody/workspace/homelab
docker stack deploy -c stacks/apps/whoami/docker-compose.yml test-stack
```

#### 3.2 Run New Teardown (DRY RUN FIRST!)

```bash
cd ansible

# Dry run (shows what WOULD happen)
ansible-playbook playbooks/cluster/teardown.yml \
  -e "confirm_teardown=true" \
  --check

# Actual teardown (destructive!)
ansible-playbook playbooks/cluster/teardown.yml \
  -e "confirm_teardown=true"
```

**Expected Output:**
```
TEARDOWN PLAN:
================
Phase 1: Remove all Docker Swarm stacks
Phase 2: Remove orphaned containers
Phase 3: Remove overlay networks (with VIP release)
Phase 4: Remove volumes (DISABLED)
Phase 5: Unmount OCFS2 filesystems
Phase 6: Logout from iSCSI sessions
Phase 7: Clean /etc/fstab entries
Phase 8: Force nodes to leave swarm (ENABLED)
Phase 9: Verification and reporting

✅ All requested resources successfully removed
```

#### 3.3 Verify Clean State

```bash
# Check Docker resources
ansible all -m command -a "docker stack ls"
ansible all -m command -a "docker network ls --filter driver=overlay"
ansible all -m command -a "docker volume ls"

# Check mounts
ansible all -m command -a "mount | grep ocfs2"

# Check iSCSI sessions
ansible all -m command -a "iscsiadm -m session"

# Check swarm state
ansible all -m command -a "docker info --format '{{.Swarm.LocalNodeState}}'"
```

**Expected:** All should show empty/inactive/none

---

### Phase 4: Test Refactored Init/Join (30 minutes)

#### 4.1 Re-initialize Swarm

```bash
# Initialize swarm on manager with verification
ansible-playbook playbooks/cluster/init-refactored.yml
```

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════╗
║          SWARM INITIALIZATION COMPLETE
╚══════════════════════════════════════════════════════════════╝

✓ Swarm is active
✓ Node is a manager
✓ Node status is Ready
✓ Network 'traefik-public' created and configured
✓ Labels applied: {'gpu': 'true', 'traefik': 'true', 'dns': 'true'}

Worker Join Command: docker swarm join --token SWMTKN-...
```

#### 4.2 Join Workers

```bash
# Get join token from init output
MANAGER_IP="192.168.86.227"  # Update with your manager IP
WORKER_TOKEN="SWMTKN-..."     # From init output

# Join workers with verification
ansible-playbook playbooks/cluster/join-refactored.yml \
  -e "manager_ip=$MANAGER_IP" \
  -e "manager_token=$WORKER_TOKEN"
```

**Expected Output (per worker):**
```
╔══════════════════════════════════════════════════════════════╗
║          WORKER NODE JOIN COMPLETE
╚══════════════════════════════════════════════════════════════╝

✓ Node is in swarm
✓ Node is a worker
✓ Node status is Ready
✓ Node is reachable from manager
✓ Labels applied

Cluster Size: 4 node(s)
- Managers: 1
- Workers:  3
```

---

### Phase 5: Test DNS/Uptime Kuma Verification (30 minutes)

#### 5.1 Update DNS Role

Replace `ansible/roles/dns/tasks/add-service-cnames.yml` with the refactored version:

```bash
cd /home/cody/workspace/homelab/ansible
mv roles/dns/tasks/add-service-cnames.yml roles/dns/tasks/add-service-cnames-OLD.yml
mv roles/dns/tasks/add-service-cnames-refactored.yml roles/dns/tasks/add-service-cnames.yml
```

#### 5.2 Update Uptime Kuma Role

```bash
mv roles/uptime_kuma/tasks/add-service-monitors.yml roles/uptime_kuma/tasks/add-service-monitors-OLD.yml
mv roles/uptime_kuma/tasks/add-service-monitors-refactored.yml roles/uptime_kuma/tasks/add-service-monitors.yml
```

#### 5.3 Test DNS Registration

```bash
# Deploy a stack with Traefik labels
ansible-playbook playbooks/deploy/stack.yml -e stack_name=whoami

# Manually trigger DNS registration
ansible-playbook playbooks/dns.yml -e dns_action=add_service_records
```

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════╗
║          DNS REGISTRATION COMPLETE
╚══════════════════════════════════════════════════════════════╝

Services Registered: 1
DNS Verified:        1
API Verified:        1

✓ DNS record for whoami.example.com resolves to: 192.168.86.227

✅ All DNS records created and verified
```

#### 5.4 Test Uptime Kuma Registration

```bash
ansible-playbook playbooks/uptime-kuma.yml -e uptime_action=add_services
```

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════╗
║          UPTIME KUMA REGISTRATION COMPLETE
╚══════════════════════════════════════════════════════════════╝

Services Discovered: 1
Newly Created:       1
Already Existed:     0
Active Monitors:     1

✅ All monitors created, verified, and active
```

---

## Rollback Procedure

If something goes wrong, you can roll back:

### Option 1: Restore Original Files

```bash
cd /home/cody/workspace/homelab/ansible

# Restore original DNS task
mv roles/dns/tasks/add-service-cnames-OLD.yml roles/dns/tasks/add-service-cnames.yml

# Restore original Uptime Kuma task
mv roles/uptime_kuma/tasks/add-service-monitors-OLD.yml roles/uptime_kuma/tasks/add-service-monitors.yml

# Remove storage role from bootstrap
git checkout playbooks/bootstrap.yml
```

### Option 2: Use Git

```bash
cd /home/cody/workspace/homelab
git status  # Review changes
git diff    # See what changed
git checkout -- ansible/  # Restore all Ansible files
```

---

## Key Differences: Old vs New

### Teardown Operations

| Feature | Old (teardown.yml) | New (cluster/teardown.yml) |
|---------|-------------------|---------------------------|
| Stack removal | ✅ Yes | ✅ Yes + verification |
| Container removal | ⚠️ failed_when: false | ✅ With verification |
| Volume removal | ✅ Basic | ✅ With driver check |
| **Network removal** | ❌ **MISSING** | ✅ **With VIP release retry** |
| **iSCSI/OCFS2 unmount** | ❌ **MISSING** | ✅ **Full teardown** |
| **Fstab cleanup** | ❌ **MISSING** | ✅ **Removes entries** |
| Swarm leave | ⚠️ ignore_errors | ✅ With state verification |
| Verification | ❌ None | ✅ After every phase |
| Reporting | ✅ Basic | ✅ Comprehensive |

### Storage Setup

| Feature | Old (common role) | New (storage role) |
|---------|------------------|-------------------|
| Code duplication | ❌ 427 lines (3x) | ✅ 50 lines (loop) |
| Module usage | ❌ shell/command | ✅ community.general.open_iscsi |
| Mount verification | ⚠️ Partial | ✅ Full (stat, write test) |
| Session verification | ❌ None | ✅ iscsiadm -m session |
| Block device wait | ✅ Yes | ✅ Yes + verification |
| Cluster test | ✅ Yes (1 mount) | ✅ Yes (all mounts) |

### Cluster Operations

| Feature | Old (init.yml) | New (init-refactored.yml) |
|---------|---------------|--------------------------|
| Module usage | ❌ command | ✅ community.docker.docker_swarm |
| Swarm verification | ❌ None | ✅ docker_swarm_info |
| Manager verification | ❌ None | ✅ Assert manager role |
| Network creation | ✅ Yes | ✅ Yes + verification |
| Network verification | ❌ None | ✅ driver + attachable check |
| Token retrieval | ⚠️ command | ✅ docker_swarm_info |
| Label verification | ❌ None | ✅ docker_node_info |

### DNS/Uptime Kuma

| Feature | Old | New |
|---------|-----|-----|
| DNS creation | ✅ Yes | ✅ Yes |
| **DNS dig verification** | ❌ **MISSING** | ✅ **dig query** |
| DNS API verification | ❌ None | ✅ API GET request |
| Uptime Kuma creation | ✅ Yes | ✅ Yes |
| **Monitor active check** | ❌ **MISSING** | ✅ **API verify** |
| **Monitor status check** | ❌ **MISSING** | ✅ **Heartbeat check** |

---

## Validation Checklist

After migrating to the refactored version, verify:

### Storage
- [ ] iSCSI sessions active: `ansible all -m command -a "iscsiadm -m session"`
- [ ] OCFS2 mounts present: `ansible all -m command -a "mount | grep ocfs2"`
- [ ] Cluster test passes: Files visible on all nodes
- [ ] Write test succeeds: Can create files on all mounts

### Cluster
- [ ] Swarm active: `ansible all -m command -a "docker info --format '{{.Swarm.LocalNodeState}}'"`
- [ ] All nodes Ready: `ansible managers -m command -a "docker node ls"`
- [ ] Networks exist: `ansible managers -m command -a "docker network ls --filter driver=overlay"`
- [ ] Labels applied: `ansible managers -m command -a "docker node inspect <hostname> --format '{{json .Spec.Labels}}'"`

### DNS
- [ ] Records resolve: `dig +short whoami.example.com @<dns-server>`
- [ ] API shows records: Check Technitium web UI

### Uptime Kuma
- [ ] Monitors exist: Check Uptime Kuma web UI
- [ ] Monitors active: Green checkmarks
- [ ] Monitors pinging: Latest heartbeat visible

### Teardown
- [ ] All stacks removed: `docker stack ls` → empty
- [ ] Networks cleaned: Only ingress/docker_gwbridge remain
- [ ] Mounts unmounted: `mount | grep ocfs2` → empty
- [ ] Sessions logged out: `iscsiadm -m session` → no sessions
- [ ] Fstab cleaned: `grep ocfs2 /etc/fstab` → empty
- [ ] Swarm left: `docker info --format '{{.Swarm.LocalNodeState}}'` → inactive

---

## Troubleshooting

### Issue: Collection not found

**Error:** `ERROR! couldn't resolve module/action 'community.docker.docker_swarm'`

**Fix:**
```bash
ansible-galaxy collection install -r requirements.yml --force
```

### Issue: Teardown fails at network removal

**Error:** `network in use`

**Fix:** The new teardown includes VIP release retry logic. If it still fails:
```bash
# Manually remove services first
docker service ls --format '{{.ID}}' | xargs docker service rm

# Wait 30 seconds
sleep 30

# Re-run teardown
ansible-playbook playbooks/cluster/teardown.yml -e "confirm_teardown=true"
```

### Issue: iSCSI sessions won't logout

**Error:** `iscsiadm: cannot logout from session`

**Fix:**
```bash
# Unmount filesystems first
ansible all -b -m command -a "umount -f /mnt/iscsi-media-apps"

# Stop OCFS2 services
ansible all -b -m systemd -a "name=o2cb state=stopped"

# Re-run teardown
ansible-playbook playbooks/cluster/teardown.yml -e "confirm_teardown=true"
```

### Issue: DNS verification fails

**Error:** `dig +short returns empty`

**Fix:**
```bash
# Check Technitium is running
curl http://192.168.86.227:5380/api/zones/list?token=...

# Check DNS server is correct
dig +short whoami.example.com @192.168.86.227

# Manual record verification
dig whoami.example.com @192.168.86.227 +trace
```

---

## Performance Improvements

### Before Refactor:
- Storage setup: ~180 lines x 3 mounts = 540 lines executed
- No verification = unknown failures
- Teardown incomplete = manual cleanup required

### After Refactor:
- Storage setup: ~60 lines for all 3 mounts (loop-based)
- Full verification = failures detected immediately
- Teardown complete = no manual cleanup

**Estimated Time Savings:**
- Initial setup: Same (verification adds ~30s)
- Debugging failures: **-2 hours** (verification catches issues early)
- Teardown: **-1 hour** (no manual cleanup)
- Re-deployment: **-30 minutes** (clean state guaranteed)

---

## Next Steps

After successful migration:

1. **Update documentation** - Document the new verification features
2. **Create backup playbook** - Save current working state
3. **Train team** - Share new playbook usage patterns
4. **Monitor production** - Watch for issues in first week
5. **Optimize further** - Consider additional verification points

---

## Support

If you encounter issues during migration:

1. Check the AUDIT_REPORT.md for detailed analysis
2. Review logs in `/tmp/teardown-report-*.txt`
3. Test with `--check` mode first
4. Roll back if necessary (see Rollback Procedure)

---

**Generated:** 2026-03-11
**Version:** 1.0
**Author:** Senior DevOps Architect
