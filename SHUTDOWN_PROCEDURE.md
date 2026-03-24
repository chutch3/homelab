# Homelab Shutdown Procedure

This document outlines the safe shutdown procedure for the entire homelab, designed to prevent data loss or corruption, especially when performing maintenance on the NAS.

**Core Principle:** Services must be stopped and all shared storage (iSCSI/OCFS2, CIFS) must be cleanly detached from cluster nodes *before* the NAS is powered off.

---

### **Step 1: Stop All Docker Stacks**

First, stop all running applications on the Docker Swarm cluster. This process also handles unmounting the CIFS volumes, which can take several minutes per service.

1.  SSH into your Docker Swarm **manager node**.
2.  List all running application stacks to see what needs to be stopped:
    ```bash
    docker stack ls
    ```
3.  For each stack listed in the output, tear it down using the `docker stack rm` command. Repeat this for every stack.
    ```bash
    docker stack rm <stack_name>
    ```
    > **Note:** Be patient, as this step can take 10-15 minutes to complete while Docker waits for CIFS volumes to unmount cleanly.

---

### **Step 2: Verify Services and Mounts are Down**

Confirm that all services are stopped and that the network-mounted CIFS volumes are no longer attached to any node.

1.  On the **manager node**, verify that no services remain:
    ```bash
    docker service ls
    ```
    *(This command should return an empty list.)*

2.  On **each cluster node** (managers and workers), verify that no CIFS shares are mounted:
    ```bash
    mount | grep cifs
    ```
    *(This command should produce no output.)*

---

### **Step 3: Unmount the OCFS2 Cluster Filesystem**

This step must be performed on **every node** in the cluster.

1.  SSH into **each node** (e.g., `node-1`, `node-2`, etc.).
2.  Unmount the shared OCFS2 filesystem:
    ```bash
    sudo umount /mnt/iscsi/media-apps
    ```
3.  Verify that the filesystem is no longer mounted:
    ```bash
    mount | grep ocfs2
    ```
    *(This command should produce no output.)*

---

### **Step 4: Disconnect iSCSI Storage**

Log out of the iSCSI storage session on **every node** to cleanly sever the connection to the NAS block device.

1.  SSH into **each node**.
2.  Log out of all iSCSI sessions:
    ```bash
    sudo iscsiadm -m node --logoutall
    ```
3.  Verify that the sessions are closed:
    ```bash
    sudo iscsiadm -m session
    ```
    *(This should report "No active sessions.")*

---

### **Step 5: Shut Down Cluster Nodes**

With all storage now safely detached, you can power off the compute nodes.

1.  First, shut down all **worker nodes**. On each worker, run:
    ```bash
    sudo shutdown now
    ```
2.  After the workers are off, shut down the **manager node(s)**:
    ```bash
    sudo shutdown now
    ```

---

### **Step 6: Shut Down the NAS**

After confirming that all cluster nodes are powered off, the NAS is no longer serving any data and can be safely shut down according to its specific procedure (e.g., via its web administration panel or power button).
