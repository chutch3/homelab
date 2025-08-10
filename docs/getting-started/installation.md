# Installation Guide

This comprehensive guide will walk you through setting up the Selfhosted platform from scratch.

## System Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 50 GB | 100+ GB SSD |
| **Network** | 100 Mbps | 1 Gbps |

### Software Requirements

=== "Ubuntu 22.04 LTS (Recommended)"

    ```bash
    # Update system packages
    sudo apt update && sudo apt upgrade -y

    # Install required packages
    sudo apt install -y curl wget git unzip
    ```

=== "Debian 11+"

    ```bash
    # Update system packages
    sudo apt update && sudo apt upgrade -y

    # Install required packages
    sudo apt install -y curl wget git unzip
    ```

=== "CentOS/RHEL 8+"

    ```bash
    # Update system packages
    sudo dnf update -y

    # Install required packages
    sudo dnf install -y curl wget git unzip
    ```

=== "macOS"

    ```bash
    # Install Homebrew if not already installed
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Install required packages
    brew install git curl wget
    ```

## Docker Installation

### Install Docker Engine

=== "Ubuntu/Debian"

    ```bash
    # Remove old Docker versions
    sudo apt remove -y docker docker-engine docker.io containerd runc

    # Add Docker GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group
    sudo usermod -aG docker $USER
    newgrp docker
    ```

=== "CentOS/RHEL"

    ```bash
    # Remove old Docker versions
    sudo dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine

    # Add Docker repository
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

    # Install Docker
    sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    sudo systemctl start docker
    sudo systemctl enable docker

    # Add user to docker group
    sudo usermod -aG docker $USER
    newgrp docker
    ```

=== "macOS"

    1. Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
    2. Install the application
    3. Start Docker Desktop
    4. Verify installation in terminal

### Verify Docker Installation

```bash
# Check Docker version
docker --version
# Expected: Docker version 24.0.0 or higher

# Check Docker Compose version
docker compose version
# Expected: Docker Compose version 2.x.x or higher

# Test Docker installation
docker run hello-world
```

## Domain & DNS Setup

### 1. Register a Domain

Choose a domain registrar and register your domain. Popular options:

- [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) (Recommended)
- [Namecheap](https://www.namecheap.com/)
- [Google Domains](https://domains.google/)

### 2. Configure Cloudflare DNS

!!! warning "Required"
    Cloudflare DNS is required for automatic SSL certificate generation.

1. **Add your domain to Cloudflare:**
   - Sign up at [Cloudflare](https://www.cloudflare.com/)
   - Add your domain to your account
   - Update nameservers at your registrar

2. **Create DNS records:**
   ```
   Type: A
   Name: *
   Content: YOUR_SERVER_IP
   TTL: Auto
   Proxy status: DNS only (gray cloud)
   ```

3. **Get API credentials** (choose one method):

=== "API Token (Recommended)"

    1. Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens)
    2. Click "Create Token"
    3. Use "Custom token" template
    4. Configure permissions:
       - `Zone:DNS:Edit`
       - `Zone:Zone:Read`
    5. Set zone resources to include your domain
    6. Create and copy the token

=== "Global API Key (Legacy)"

    1. Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens)
    2. Click "View" next to "Global API Key"
    3. Enter your password
    4. Copy the key

## Selfhosted Platform Installation

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/homelab.git
cd homelab

# Verify the installation
ls -la
```

Expected structure:
```
homelab/
├── config/
├── docs/
├── scripts/
├── tests/
├── selfhosted.sh
├── pyproject.toml
└── README.md
```

### 2. Initialize Configuration

```bash
# Initialize environment configuration
./selfhosted config init
```

This command will:

- Copy `.env.example` to `.env`
- Create necessary directories
- Set proper permissions
- Validate basic configuration

### 3. Configure Environment Variables

Edit your `.env` file:

```bash
nano .env
```

**Essential Configuration:**

```bash title=".env"
# ===========================================
# DOMAIN CONFIGURATION
# ===========================================
BASE_DOMAIN=yourdomain.com
WILDCARD_DOMAIN=*.yourdomain.com

# ===========================================
# CLOUDFLARE API CONFIGURATION
# ===========================================
# Choose ONE method:

# Method 1: API Token (Recommended)
CF_Token=your_cloudflare_api_token

# Method 2: Global API Key (Legacy)
# CF_Email=your@email.com
# CF_Key=your_global_api_key

# ===========================================
# DOCKER CONFIGURATION
# ===========================================
UID=1000
GID=1000

# ===========================================
# SSH CONFIGURATION (for multi-node)
# ===========================================
SSH_KEY_FILE=~/.ssh/id_rsa
SSH_TIMEOUT=30

# ===========================================
# SECURITY CONFIGURATION
# ===========================================
ADMIN_EMAIL=admin@yourdomain.com
TIMEZONE=America/New_York
```

### 4. Validate Configuration

```bash
# Validate your configuration
./selfhosted config validate
```

Expected output:
```
✅ Configuration validation completed successfully
✅ Environment variables are properly set
✅ Docker is running and accessible
✅ Cloudflare API credentials are valid
✅ Domain configuration is correct
```

## Development Environment (Optional)

If you plan to contribute or customize the platform:

### 1. Install Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 2. Install Development Dependencies

```bash
# Install all dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install
```

### 3. Install Task Runner

```bash
# Install Task (optional but recommended)
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d ~/.local/bin
```

## Verification

### 1. Test Basic Functionality

```bash
# List available services
./selfhosted service list

# Check service information
./selfhosted service info homepage

# Validate services configuration
./selfhosted service validate
```

### 2. Test Deployment Generation

```bash
# Generate deployment files
./selfhosted service generate

# Check generated files
ls -la generated/
```

### 3. Test Container Functionality

```bash
# Test Docker connectivity
docker ps

# Test Docker Compose
docker compose version
```

## Next Steps

<div class="grid cards" markdown>

- :material-rocket-launch: **[Quick Start](quick-start.md)**

    ---

    Deploy your first service in 5 minutes

- :material-cog: **[Configuration](configuration.md)**

    ---

    Learn about advanced configuration options

- :material-play: **[First Deployment](first-deployment.md)**

    ---

    Step-by-step guide to your first deployment

</div>

## Troubleshooting

??? question "Docker permission denied?"

    Make sure your user is in the docker group:
    ```bash
    sudo usermod -aG docker $USER
    newgrp docker
    ```

??? question "Cloudflare API not working?"

    Test your API credentials:
    ```bash
    curl -X GET "https://api.cloudflare.com/client/v4/zones" \
         -H "Authorization: Bearer YOUR_TOKEN" \
         -H "Content-Type: application/json"
    ```

??? question "Domain not resolving?"

    Check your DNS configuration:
    ```bash
    dig @8.8.8.8 yourdomain.com
    nslookup yourdomain.com
    ```

??? question "Services won't start?"

    Check Docker logs:
    ```bash
    docker compose logs
    ```

[Need more help? See our full troubleshooting guide →](../user-guide/troubleshooting.md)
