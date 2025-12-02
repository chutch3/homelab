# Prerequisites & System Setup

This guide covers all the prerequisite setup steps needed before deploying the homelab. These are one-time setup tasks for preparing your infrastructure.

## Overview

You'll need to set up:

1. **Docker Environment** - Sudoless Docker access on all nodes
2. **Network Storage** (Optional) - OpenMediaVault or NAS with CIFS/SMB
3. **Cloudflare** - Domain and API access for SSL certificates
4. **SSH Access** - Key-based authentication between nodes

---

## 1. Docker Installation & Sudoless Access

### Install Docker

Install Docker on all nodes (manager and workers):

=== "Ubuntu/Debian"
    ```bash
    # Install Docker using official script
    curl -fsSL https://get.docker.com | sh

    # Verify installation
    docker --version
    docker compose version
    ```

=== "Manual Installation"
    ```bash
    # Update packages
    sudo apt update
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

### Enable Sudoless Docker Access

**Why?** The deployment scripts need to run Docker commands without `sudo`. This requires adding your user to the `docker` group.

```bash
# Add current user to docker group
sudo usermod -aG docker $USER

# Apply the new group membership
newgrp docker

# Verify sudoless access works
docker ps
```

**Important:** Run this on **all nodes** (manager and workers).

!!! warning "Logout Required"
    You may need to log out and back in for the group membership to take effect. If `newgrp docker` doesn't work, try:
    ```bash
    sudo su - $USER
    ```

### Test Docker Access

Verify Docker works without sudo:

```bash
# Should work without sudo
docker run hello-world

# Check Docker Compose
docker compose version
```

---

## 2. Network Storage Setup (Optional)

If you want to store service data on a NAS, you'll need to set up CIFS/SMB mounting.

### Option A: OpenMediaVault (OMV)

[OpenMediaVault](https://www.openmediavault.org/) is a free NAS solution perfect for homelabs.

#### Install OpenMediaVault

On your dedicated NAS machine:

```bash
# Download and install OMV
wget -O - https://raw.githubusercontent.com/OpenMediaVault-Plugin-Developers/installScript/master/install | sudo bash
```

The installer will:

- Install OpenMediaVault
- Set up the web interface (default port 80)
- Display the admin credentials

#### Initial OMV Configuration

1. **Access Web Interface**
   ```
   http://nas-ip-address
   Default: admin / openmediavault
   ```

2. **Create Storage**
    - Navigate to **Storage → Disks**
    - Wipe and format your data disk
    - **Storage → File Systems** → Create filesystem (ext4 recommended)
    - Mount the filesystem

3. **Create Shared Folder**
    - **Storage → Shared Folders** → Create
    - Name: `homelab` (or your preference)
    - Device: Select your mounted filesystem
    - Path: `/homelab/`
    - Permissions: Read/Write for users

4. **Enable SMB/CIFS**
    - **Services → SMB/CIFS** → Settings
    - Enable SMB/CIFS
    - Set workgroup (default: WORKGROUP)
    - Save and apply

5. **Share the Folder**
    - **Services → SMB/CIFS → Shares** → Add
    - Shared folder: Select `homelab`
    - Public: No
    - Guest access: No
    - Save and apply

6. **Create SMB User**
    - **Users → Users** → Add
    - Username: `homelab`
    - Password: (strong password)
    - Groups: Add to `users`
    - Save

### Option B: Existing NAS

If you already have a NAS (Synology, QNAP, TrueNAS, etc.):

1. Create a shared folder for homelab data
2. Enable SMB/CIFS service
3. Create a user with read/write access
4. Note the share path (e.g., `//nas-ip/homelab`)

### Install CIFS Utils on Docker Nodes

Install CIFS utilities on **all Docker nodes** that will mount network storage:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y cifs-utils

# Verify installation
mount.cifs -V
```

### Test NAS Connection

From your Docker nodes:

```bash
# Create test mount point
sudo mkdir -p /mnt/nas-test

# Test mount (replace with your NAS details)
sudo mount -t cifs //NAS_IP/homelab /mnt/nas-test -o username=homelab,password=YOUR_PASSWORD

# Verify mount
ls /mnt/nas-test

# Create test file
sudo touch /mnt/nas-test/test.txt
ls /mnt/nas-test

# Unmount
sudo umount /mnt/nas-test
```

!!! success "Mount Successful"
    If you can create files and see them, your NAS is configured correctly!

### Configure NAS in .env

Add NAS details to your `.env` file:

```bash
# NAS Configuration
NAS_SERVER=192.168.1.50          # Your NAS IP or hostname
SMB_USERNAME=homelab              # SMB/CIFS username
SMB_PASSWORD=your_secure_password # SMB/CIFS password
NAS_SHARE=/homelab                # Share name
```

---

## 3. Cloudflare Setup

Cloudflare provides free SSL certificates and DNS management.

### Create Cloudflare Account

1. Go to [cloudflare.com](https://cloudflare.com)
2. Sign up for a free account
3. Add your domain

### Add Your Domain

1. Click "Add Site" in the Cloudflare dashboard
2. Enter your domain name
3. Select the Free plan
4. Cloudflare will scan your existing DNS records
5. Update your domain's nameservers at your registrar to point to Cloudflare's nameservers

!!! info "Nameserver Update"
    ```
    Cloudflare nameservers (example):
    ns1.cloudflare.com
    ns2.cloudflare.com
    ```

    This can take 24-48 hours to propagate, but usually happens within an hour.

### Create DNS Wildcard Record

Once your domain is active on Cloudflare:

1. Go to **DNS → Records**
2. Add a new record:
   ```
   Type: A
   Name: *
   IPv4 address: YOUR_SERVER_IP
   Proxy status: DNS only (gray cloud ☁️)
   TTL: Auto
   ```

!!! warning "Proxy Status"
    Set to **DNS only** (gray cloud), not Proxied (orange cloud). Traefik needs direct access for SSL certificate validation.

### Generate API Token

The homelab needs a Cloudflare API token to automatically create SSL certificates.

1. Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click **"Create Token"**
3. Click **"Use template"** next to **"Edit zone DNS"**
4. Configure the token:
   ```
   Token name: Homelab SSL
   Permissions:
     - Zone:DNS:Edit
     - Zone:Zone:Read
   Zone Resources:
     - Include → Specific zone → yourdomain.com
   ```
5. Click **"Continue to summary"**
6. Review and click **"Create Token"**
7. **Copy the token** - you won't be able to see it again!

### Save API Token

Add to your `.env` file:

```bash
# Cloudflare Configuration
BASE_DOMAIN=yourdomain.com
CF_Token=your_cloudflare_api_token_here
ACME_EMAIL=admin@yourdomain.com
```

### Test DNS Resolution

Verify your wildcard DNS is working:

```bash
# Test various subdomains
nslookup test.yourdomain.com
nslookup homeassistant.yourdomain.com
nslookup traefik.yourdomain.com

# All should resolve to your server IP
```

---

## 4. SSH Key Setup

The cluster management scripts use SSH to communicate between nodes.

### Generate SSH Key

On your **manager node**:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/selfhosted_rsa -N ""

# This creates:
# - ~/.ssh/selfhosted_rsa (private key)
# - ~/.ssh/selfhosted_rsa.pub (public key)
```

### Copy SSH Key to All Nodes

Copy the public key to all worker nodes:

```bash
# For each worker node
ssh-copy-id -i ~/.ssh/selfhosted_rsa.pub user@worker-node-ip

# Example:
ssh-copy-id -i ~/.ssh/selfhosted_rsa.pub ubuntu@192.168.1.101
ssh-copy-id -i ~/.ssh/selfhosted_rsa.pub ubuntu@192.168.1.102
```

### Test SSH Access

Verify passwordless SSH works:

```bash
# Should connect without password prompt
ssh -i ~/.ssh/selfhosted_rsa user@worker-node-ip

# Test command execution
ssh -i ~/.ssh/selfhosted_rsa user@worker-node-ip "docker ps"
```

### Configure SSH Key Path

The default SSH key path is `~/.ssh/selfhosted_rsa`. If you use a different path, set it in your environment:

```bash
export SSH_KEY_FILE=~/.ssh/your_custom_key
```

Or add to `.env`:

```bash
SSH_KEY_FILE=/home/user/.ssh/custom_key
```

---

## 5. System Requirements Checklist

Before proceeding with deployment, verify:

### All Nodes (Manager + Workers)

- [ ] Docker installed and running
- [ ] Current user in `docker` group (sudoless access)
- [ ] CIFS utils installed (if using NAS)
- [ ] SSH access configured from manager
- [ ] Required ports open (see below)

### Network Storage (if applicable)

- [ ] NAS/OMV installed and accessible
- [ ] SMB/CIFS share created
- [ ] User credentials configured
- [ ] Test mount successful from all nodes

### Cloudflare

- [ ] Domain added to Cloudflare
- [ ] Nameservers updated and active
- [ ] Wildcard DNS record created (*. yourdomain.com)
- [ ] API token generated with correct permissions

### Network

- [ ] All nodes can communicate with each other
- [ ] Required ports are open (see below)

---

## 6. Required Ports

Ensure these ports are open between nodes:

### Docker Swarm Ports

```bash
# Manager node
2377/tcp   # Swarm cluster management
7946/tcp   # Container network discovery
7946/udp   # Container network discovery
4789/udp   # Container overlay network

# If using UFW
sudo ufw allow 2377/tcp
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp
sudo ufw allow 4789/udp
```

### Service Ports

```bash
80/tcp     # HTTP (Traefik)
443/tcp    # HTTPS (Traefik)
5380/tcp   # DNS Server Web UI (optional external access)
```

---

## Troubleshooting

### Docker Permission Denied

**Error:** `permission denied while trying to connect to the Docker daemon socket`

**Solution:**
```bash
# Verify user is in docker group
groups $USER

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or restart session
logout
```

### NAS Mount Fails

**Error:** `mount error(13): Permission denied`

**Check:**
1. Verify SMB credentials are correct
2. Check NAS share permissions
3. Verify CIFS utils installed: `dpkg -l | grep cifs-utils`

**Test manually:**
```bash
sudo mount -t cifs //NAS_IP/share /mnt/test \
  -o username=user,password=pass,vers=3.0
```

### Cloudflare API Token Invalid

**Error:** `Error getting DNS token` or `authentication failed`

**Check:**
1. Token has `Zone:DNS:Edit` and `Zone:Zone:Read` permissions
2. Token is scoped to the correct zone/domain
3. Token hasn't expired
4. No typos in `.env` file

**Test token:**
```bash
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type:application/json"
```

### SSH Connection Fails

**Error:** `Permission denied (publickey)`

**Check:**
1. Public key is in `~/.ssh/authorized_keys` on worker node
2. SSH key permissions: `chmod 600 ~/.ssh/selfhosted_rsa`
3. Correct username for worker node

**Debug:**
```bash
ssh -v -i ~/.ssh/selfhosted_rsa user@worker-ip
```

---

## Next Steps

Once all prerequisites are complete:

1. [Configure machines.yaml](configuration.md) - Define your cluster nodes
2. [Configure .env](configuration.md) - Set environment variables
3. [First Deployment](first-deployment.md) - Deploy your homelab

---

**Need help?** Open an issue on [GitHub](https://github.com/chutch3/selfhosted.sh/issues).
