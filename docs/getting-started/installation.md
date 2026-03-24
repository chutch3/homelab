# Full Installation Guide

This guide walks through the complete installation of the homelab platform, from initial configuration to full deployment of infrastructure and applications.

!!! info "Prerequisites Required"
    Before installing, ensure you have completed the [Prerequisites](prerequisites.md) guide to set up:
    - Target nodes with compatible OS (Ubuntu 22.04+ or Debian 11+)
    - SSH key-based access between your control machine and all nodes
    - Cloudflare domain and API token
    - (Optional) Network storage (NAS/OMV with CIFS/iSCSI)

---

## Step 1: Clone and Prepare

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/chutch3/homelab.git
    cd homelab
    ```

2.  **Install dependencies:**
    The project uses Ansible for automation. Install it and other requirements via Task:
    ```bash
    task ansible:install
    ```

---

## Step 2: Configuration

### 1. Configure Host Inventory
Create your cluster configuration in the Ansible inventory:

```bash
# Create and edit your hosts file
nano ansible/inventory/02-hosts.yml
```

Example multi-node configuration:
```yaml title="ansible/inventory/02-hosts.yml"
all:
  children:
    managers:
      hosts:
        manager-01:
          ansible_host: 192.168.1.100
          ansible_user: ubuntu
    workers:
      hosts:
        worker-01:
          ansible_host: 192.168.1.101
          ansible_user: ubuntu
          node_labels:
            gpu: true
```

### 2. Configure Environment Variables
Create your `.env` file from the provided example:

```bash
cp .env.example .env
nano .env
```

**Essential Configuration:**
```bash title=".env"
# Domain Configuration
BASE_DOMAIN=yourdomain.com
CF_Token=your_cloudflare_api_token
ACME_EMAIL=admin@yourdomain.com

# User IDs (usually 1000 for the first user)
UID=1000
GID=1000

# Service Credentials (generate secure values)
DNS_ADMIN_PASSWORD=secure_password
GRAFANA_ADMIN_PASSWORD=secure_password
```

See the [Configuration Guide](configuration.md) for a full list of available variables.

---

## Step 3: Deployment

The deployment process is split into bootstrapping the nodes and then deploying the cluster.

1.  **Bootstrap Nodes:**
    Prepares all nodes with Docker, dependencies, and security hardening.
    ```bash
    task ansible:bootstrap
    ```

2.  **Initialize Cluster & Deploy:**
    Initializes Docker Swarm and deploys all infrastructure and application stacks.
    ```bash
    task ansible:deploy
    ```

### What Happens During Deployment?
- **Docker Swarm**: A multi-node cluster is initialized and joined.
- **Networking**: An overlay network (`traefik-public`) is created for service communication.
- **Core Infrastructure**:
    - **Traefik**: Reverse proxy with automatic SSL (Let's Encrypt).
    - **Technitium DNS**: Internal DNS resolution.
    - **Monitoring**: Prometheus, Grafana, Loki, and Promtail.
- **Applications**: All services in `stacks/apps/` are deployed according to their configurations.
- **DNS Registration**: A/CNAME records are automatically added for all services.

---

## Step 4: Verification

Check that all services are running correctly:

1.  **Check Stack Status:**
    ```bash
    docker stack ls
    ```

2.  **Check Individual Services:**
    ```bash
    docker service ls
    ```

3.  **View Logs (example for Traefik):**
    ```bash
    docker service logs reverse-proxy_traefik --tail 50 -f
    ```

---

## Step 5: Access Your Services

Once deployment completes, access your services via their configured domains:

- **Homepage Dashboard**: `https://homepage.yourdomain.com`
- **Traefik Dashboard**: `https://traefik.yourdomain.com`
- **Grafana Monitoring**: `https://grafana.yourdomain.com`
- **DNS Server**: `http://dns.yourdomain.com:5380`

---

## Management Commands

### Service Operations
```bash
# Deploy or update a specific service
task ansible:deploy:service -- -e "stack_name=homeassistant"

# Tear down a specific service (preserves volumes)
task ansible:teardown:service -- -e "stack_name=homeassistant"

# Tear down a service and DELETE its data (Destructive)
task ansible:teardown:service -- -e "stack_name=homeassistant remove_volumes=true"
```

### Cluster Operations
```bash
# Check cluster health
task ansible:cluster:status

# Full cluster teardown (preserves volumes)
task ansible:teardown

# Full cluster teardown including volumes (Destructive)
task ansible:teardown:with-volumes
```

---

## Troubleshooting

??? question "Docker permission denied?"
    Ensure your user is in the `docker` group:
    ```bash
    sudo usermod -aG docker $USER
    newgrp docker
    ```

??? question "Services stuck in 'Pending'?"
    Check service status for placement constraints or resource issues:
    ```bash
    docker service ps <service_name>
    ```

??? question "SSL certificate issues?"
    Verify your Cloudflare token and check Traefik logs:
    ```bash
    docker service logs reverse-proxy_traefik | grep -i acme
    ```

For more detailed issues, see the [Troubleshooting Guide](../troubleshooting.md).
