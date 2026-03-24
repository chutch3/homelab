# Quick Start Guide

!!! tip "Goal"
    Deploy your first self-hosted services in under 10 minutes!

## 🚀 One-Command Deployment

Once you have your prerequisites ready, you can deploy your entire homelab with these simple steps:

```bash
# 1. Clone the repository
git clone https://github.com/chutch3/homelab.git
cd homelab

# 2. Configure your environment
cp .env.example .env
nano .env  # Set your domain, Cloudflare credentials, etc.

# 3. Configure your hosts
nano ansible/inventory/02-hosts.yml # Define your manager node

# 4. Install Ansible and dependencies
task ansible:install

# 5. Bootstrap and Deploy
task ansible:bootstrap
task ansible:deploy
```

**That's it!** All **28+ services** deploy automatically with SSL certificates, DNS registration, and dashboard integration.

---

## 📋 Prerequisites Check

Before we begin, make sure you have:

- [x] **Docker Engine 24.0+** on target nodes
- [x] **Ansible** installed on your control machine (`task ansible:install`)
- [x] **Domain name** managed via Cloudflare
- [x] **Cloudflare API Token** with DNS permissions
- [x] **Linux environment** (Ubuntu 22.04+ or Debian 11+)

---

## 🛠️ Step-by-Step Details

### Step 1: Configure Your Domain
The platform uses Traefik for SSL. You need a domain on Cloudflare. Set your `BASE_DOMAIN` and `CF_Token` in the `.env` file.

### Step 2: Configure Your Hosts
Define your target server in `ansible/inventory/02-hosts.yml`. For a single-node setup, just add one manager:

```yaml title="ansible/inventory/02-hosts.yml"
all:
  children:
    managers:
      hosts:
        my-server:
          ansible_host: 192.168.1.10
          ansible_user: youruser
```

### Step 3: Choose Your Services
The platform comes with **28+ pre-configured stacks**. You can see them all in:
```bash
ls stacks/apps/
```
By default, `task ansible:deploy` will deploy all available services.

### Step 4: Access Your Services
Once deployment completes, visit your new dashboard:
- **Homepage Dashboard**: `https://homepage.yourdomain.com`

From here, you can access all other services like Home Assistant, PhotoPrism, and more.

---

## 📚 What's Next?

<div class="grid cards" markdown>

- :material-book-open-page-variant: **[Full Installation Guide](installation.md)**

    ---

    Detailed guide for multi-node setup and storage.

- :material-view-list: **[Services Catalog](../services/index.md)**

    ---

    Explore all 28+ pre-configured application stacks.

- :material-cog: **[Service Management](../user-guide/service-management.md)**

    ---

    Learn how to add, remove, and update services.

</div>
