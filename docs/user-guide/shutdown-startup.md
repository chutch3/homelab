# Shutdown and Startup Procedures

This guide provides the safe and validated procedures for shutting down and starting up the entire homelab. Following these steps is critical to prevent data corruption, especially for services relying on the OCFS2 cluster filesystem.

The core principle is to treat the NAS as the first thing on and the last thing off. All cluster nodes must have storage gracefully detached before the NAS is powered down.

---

## Shutdown Procedure

This procedure powers down all services and nodes in a controlled sequence using dedicated Taskfile commands.

**Step 1: Stop All Docker Stacks**

This command runs an Ansible playbook to remove all running stacks, which also handles the unmounting of CIFS volumes.

```bash
task ansible:teardown -- -K
```

> **Note:** This step can take 10-15 minutes as it waits for network volumes to unmount cleanly.

**Step 2: Unmount OCFS2 Filesystems**

This task runs a playbook to unmount all configured OCFS2 filesystems on all nodes.

```bash
task ansible:ocfs2:umount -- -K
```

**Step 3: Disconnect iSCSI Storage**

This task logs out from the iSCSI targets on all nodes.

```bash
task ansible:iscsi:logout -- -K
```

**Step 4: Shut Down Cluster Nodes**

Shut down the workers first, then the managers, by passing the inventory group name to the task.

1.  Shut down **worker** nodes:
    ```bash
    task ansible:nodes:shutdown -- workers -K
    ```
2.  Shut down **manager** nodes:
    ```bash
    task ansible:nodes:shutdown -- managers -K
    ```

**Step 5: Shut Down the NAS**

After confirming all cluster nodes are powered off, the NAS is no longer serving files or block storage and can be safely shut down via its administrative interface.

---

## Startup Procedure

This procedure brings the homelab back online, ensuring storage is available *before* services attempt to start.

**Step 1: Power On Hardware**

1.  Power on the **NAS** and wait for it to be fully booted and available on the network.
2.  Power on all cluster nodes (managers and workers).

**Step 2: Verify Node Connectivity**

Use the `ansible:ping` task to confirm that all nodes are online and reachable by Ansible.

```bash
task ansible:ping
```

**Step 3: Connect iSCSI Storage**

This task runs a playbook that discovers and logs into the iSCSI targets defined in your Ansible inventory.

```bash
task ansible:iscsi:login
```

**Step 4: Mount OCFS2 Filesystems**

This task mounts all configured OCFS2 filesystems.

```bash
task ansible:ocfs2:mount
```

> **Configuration Note:** For this step to work reliably, you must define the UUIDs of your OCFS2 filesystems in your Ansible inventory (e.g., `inventory/group_vars/all/main.yml`). This ensures the correct devices are mounted every time.
> ```yaml
> # inventory/group_vars/all/main.yml
> OCFS2_MEDIA_UUID: "your-media-partition-uuid"
> OCFS2_APP_DATA_UUID: "your-app-data-partition-uuid"
> ```
> You can find the UUID of a formatted partition by using the `lsblk -f` or `blkid` command on one of the nodes after connecting to the iSCSI target.

**Step 5: Deploy All Services**

Use the `ansible:deploy` task to bring all your application stacks online.

```bash
task ansible:deploy
```

Ansible will deploy all stacks defined in your `stacks.yml` file, and services will start in a controlled manner.

---

## Rebooting a Single Node

Use this procedure when you need to reboot one node (e.g. after a kernel update) without taking down the entire cluster. **The node must already be a healthy cluster member** — if it was hard-rebooted or crashed, use [`task ansible:storage:recover`](#if-a-reboot-was-not-clean) instead, which also runs `fsck.ocfs2` before remounting.

> **Note:** All services run as `replicas: 1` with strict placement constraints, so services pinned to the target node will be briefly unavailable during the reboot. Services on other nodes are unaffected.

```bash
task ansible:node:reboot -- -e "target_node=mini" -K
```

Replace `mini` with the node you want to reboot (`giant`, `imac`, or `cody-X570-GAMING-X`).

The playbook runs the following phases automatically:

1. **Drain** — marks the node unavailable in Docker Swarm so no new tasks are scheduled on it, then waits for running tasks to stop
2. **Unmount storage** — cleanly unmounts OCFS2 filesystems and disconnects iSCSI on the target node, preventing journal corruption
3. **Reboot** — reboots the node and waits for it to come back online
4. **Reconnect storage** — logs back into iSCSI and remounts OCFS2 on the rebooted node
5. **Reactivate** — sets the node back to active in Docker Swarm
6. **Redeploy** — redeploys all stacks to restore services on the node

### Rebooting the Manager Node

Rebooting `cody-X570-GAMING-X` (the Swarm manager) has higher impact:

- **Traefik goes down** — all web UIs are unreachable until the node comes back
- **DNS (Technitium) goes down** — if `SECONDARY_DNS_ENABLED=true`, Pi-hole will handle DNS during the window; otherwise DNS resolution on the network will fail

The procedure is the same:

```bash
task ansible:node:reboot -- -e "target_node=cody-X570-GAMING-X" -K
```

### If a Reboot Was Not Clean

If a node was hard-rebooted or crashed and OCFS2 journals are dirty, use the full storage recovery playbook instead:

```bash
task ansible:storage:recover
```

This stops all stacks cluster-wide, runs `fsck.ocfs2`, remounts, and redeploys.
