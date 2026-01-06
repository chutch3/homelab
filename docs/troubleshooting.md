# Troubleshooting

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
