# Shutdown and Startup

Core principle: NAS is first on, last off. Storage must be detached before the NAS powers down.

---

## Shutdown

```bash
# 1. Stop all stacks and unmount CIFS
task ansible:teardown -- -K                    # ~10-15 min

# 2. Unmount OCFS2
task ansible:ocfs2:umount -- -K

# 3. Disconnect iSCSI
task ansible:iscsi:logout -- -K

# 4. Power off nodes (workers first, then managers)
task ansible:nodes:shutdown -- workers -K
task ansible:nodes:shutdown -- managers -K

# 5. Shut down NAS via its admin interface
```

---

## Startup

```bash
# 1. Power on NAS, wait for it to be fully available
# 2. Power on all cluster nodes

# 3. Verify connectivity
task ansible:ping

# 4. Reconnect storage
task ansible:iscsi:login
task ansible:ocfs2:mount

# 5. Deploy
task ansible:deploy
```

OCFS2 mount requires UUIDs defined in `inventory/group_vars/all/main.yml`:

```yaml
OCFS2_MEDIA_UUID: "your-media-partition-uuid"
OCFS2_APP_DATA_UUID: "your-app-data-partition-uuid"
```

Find UUIDs with `lsblk -f` or `blkid` after iSCSI login.

---

## Single Node Reboot

For kernel updates or maintenance on one node without taking down the cluster.

```bash
task ansible:node:reboot -- -e "target_node=mini" -K
```

Phases: drain → unmount OCFS2/iSCSI → reboot → reconnect storage → reactivate in swarm → redeploy stacks.

Services pinned to the target node are briefly unavailable. Other nodes are unaffected.

**Manager node reboot** takes down Traefik (all web UIs) and DNS (unless `SECONDARY_DNS_ENABLED=true` for Pi-hole failover). Same command:

```bash
task ansible:node:reboot -- -e "target_node=cody-X570-GAMING-X" -K
```

---

## Unclean Reboot Recovery

If a node crashed or was hard-rebooted and OCFS2 journals are dirty:

```bash
task ansible:storage:recover
```

This stops all stacks cluster-wide, runs `fsck.ocfs2`, remounts, and redeploys.
