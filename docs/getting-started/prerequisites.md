# Prerequisites & System Setup

This guide covers all the prerequisite setup steps needed before deploying the homelab. These are one-time setup tasks for preparing your infrastructure.

## Overview

You'll need to set up:

1. **Docker Environment** - Ansible will install Docker, but you need a compatible OS.
2. **Network Storage** (Optional) - OpenMediaVault or NAS with CIFS/SMB.
3. **Cloudflare** - Domain and API access for SSL certificates.
4. **SSH Access** - Key-based authentication between your control machine and all homelab nodes.

---

## 1. Docker Installation & Sudoless Access

### OS Requirements

This playbook is tested on **Ubuntu 22.04+** and **Debian 11+**. Other Linux distributions may work but are not officially supported.

### Docker Installation

You do not need to install Docker yourself. The `ansible:bootstrap` command will automatically:
- Install the correct version of Docker and Docker Compose.
- Add your SSH user to the `docker` group for sudoless access.

---

## 2. Network Storage Setup (Optional)

If you want to store service data on a NAS, you'll need to set up CIFS/SMB mounting. The `bootstrap` playbook will install the necessary `cifs-utils` on all nodes.

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

The Ansible playbooks use SSH to communicate between nodes.

### Generate SSH Key

On your **control machine** (where you will run `task`):

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# This creates:
# - ~/.ssh/id_rsa (private key)
# - ~/.ssh/id_rsa.pub (public key)
```

### Copy SSH Key to All Nodes

The `ansible:bootstrap` command will automatically copy your public key to all nodes in your inventory. However, for this to work, you must be able to SSH into each node with a password for the *first time*.

Alternatively, you can manually copy the key:
```bash
# For each homelab node
ssh-copy-id -i ~/.ssh/id_rsa.pub user@homelab-node-ip
```

### Configure Ansible for SSH

The Ansible inventory is pre-configured to use your default SSH key (`~/.ssh/id_rsa`). If you use a different key, you can specify it in `ansible/inventory/group_vars/all.yml`:

```yaml
ansible_ssh_private_key_file: '~/.ssh/your_custom_key'
```

### Test SSH Access

Verify passwordless SSH works from your control machine to each homelab node:

```bash
# Should connect without password prompt
ssh user@homelab-node-ip

# Test command execution
ssh user@homelab-node-ip "docker ps"
```

---

## 5. System Requirements Checklist

Before proceeding with deployment, verify:

### All Nodes (Manager + Workers)

- [ ] Compatible OS (Ubuntu 22.04+ or Debian 11+)
- [ ] SSH access configured from your control machine.

### Network Storage (if applicable)

- [ ] NAS/OMV installed and accessible
- [ ] SMB/CIFS share created
- [ ] User credentials configured

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

### SSH Connection Fails

**Error:** `Permission denied (publickey)`

**Check:**
1. Your public key is in `~/.ssh/authorized_keys` on the remote node.
2. The remote user's home directory and `.ssh` directory have correct permissions (`700` for `.ssh`, `600` for `authorized_keys`).

**Debug:**
```bash
ssh -v user@homelab-node-ip
```

---

## Next Steps

Once all prerequisites are complete:

1. [Configure your inventory](configuration.md) - Define your cluster nodes in `ansible/inventory/02-hosts.yml`.
2. [Configure .env](configuration.md) - Set environment variables.
3. [First Deployment](first-deployment.md) - Deploy your homelab.

---

**Need help?** Open an issue on [GitHub](https://github.com/chutch3/homelab/issues).
