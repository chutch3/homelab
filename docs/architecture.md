# System Architecture

This document describes the architecture of the homelab system.

## Architecture Overview

The system is built on a **stacks-based architecture** using Ansible and Docker Swarm. Each service is defined in its own Docker Compose file within the `stacks/` directory. Ansible reads these files and deploys them as stacks to a Docker Swarm cluster.

```mermaid
graph TB
    subgraph "User Interface"
        USER[🧑‍💻 User] -- runs --> TASK["🔵 Taskfile.yml<br/>(e.g., task ansible:deploy:full)"]
    end

    subgraph "Configuration Files"
        DOT_ENV["📄 .env<br/>Secrets & Variables"]
        INVENTORY["⚙️ ansible/inventory/<br/>Host & Group Definitions"]
        STACKS_DIR["📁 stacks/<br/>One folder per service"]
    end

    subgraph "Orchestration Engine"
        ANSIBLE["🤖 Ansible<br/>(ansible-playbook)"]
        PLAYBOOKS["📚 ansible/playbooks/<br/>(e.g., deploy/stacks.yml)"]
    end

    subgraph "Deployment Target: Docker Swarm Cluster"
        MANAGER["👑 Manager Node"]
        WORKERS["- Worker Nodes"]
        SWARM_NETWORK["🕸️ Overlay Network<br/>(traefik-public)"]
    end

    subgraph "Core Running Services"
        TRAEFIK["🚪 Traefik<br/>(Reverse Proxy)"]
        DNS["🌐 Technitium DNS<br/>(Internal DNS)"]
        MONITORING["📊 Prometheus/Grafana<br/>(Monitoring)"]
    end

    subgraph "Application Services"
        APPS["🚀 Applications<br/>(Home Assistant, Photoprism, etc.)"]
    end

    %% Data Flow
    USER --> TASK
    TASK -- triggers --> ANSIBLE
    ANSIBLE -- reads --> PLAYBOOKS
    ANSIBLE -- uses --> DOT_ENV
    ANSIBLE -- uses --> INVENTORY
    ANSIBLE -- reads service definitions from --> STACKS_DIR

    %% Deployment Flow
    ANSIBLE -- deploys to --> MANAGER
    MANAGER -- manages --> WORKERS
    MANAGER -- creates --> SWARM_NETWORK
    MANAGER -- deploys --> TRAEFIK
    MANAGER -- deploys --> DNS
    MANAGER -- deploys --> MONITORING
    MANAGER -- deploys --> APPS

    %% Service Interaction
    TRAEFIK -- routes traffic to --> APPS
    DNS -- resolves domains for --> APPS
end
```

## Key Components

### 1. Configuration

The entire system is configured through a set of human-readable files:

- **`.env`**: The primary file for environment-specific variables like domain names, API keys, and service credentials. It is copied from `.env.example`.
- **`ansible/inventory/`**: This directory defines the infrastructure. The `01-structure.yml` file sets up the groups (managers, workers), and you define your actual hosts in a separate file like `02-hosts.yml`.
- **`stacks/`**: This is the core of the service definitions. Each subdirectory within `stacks/` (e.g., `stacks/apps/homeassistant`) represents a service and contains a `docker-compose.yml` file.

### 2. Command Interface: `Taskfile.yml`

Instead of a custom script, the project uses [Task](https://taskfile.dev/) as a command runner. The root `Taskfile.yml` and `ansible/Taskfile.yml` define all available commands for testing, linting, and deployment.

The primary entry point for deployment is through `task` commands:

```bash
# Deploy all services
task ansible:deploy:full

# Deploy a single service stack
task ansible:deploy:stack -- -e "stack_name=homeassistant"

# Tear down a single stack
task ansible:teardown:stack -- -e "stack_name=homeassistant"
```

### 3. Orchestration Engine: Ansible

Ansible is the engine that drives the entire deployment process. The `task` commands are simple wrappers around `ansible-playbook` calls.

- **Playbooks (`ansible/playbooks/`)**: These are the heart of the automation. For example, `deploy/stacks.yml` is responsible for iterating through the `stacks/` directory and deploying each `docker-compose.yml` file to the Docker Swarm. `bootstrap.yml` prepares the nodes with necessary dependencies like Docker.
- **Roles (`ansible/roles/`)**: Reusable components that perform specific tasks, like setting up the Docker repository, managing users, or installing GPU drivers.

### 4. Deployment Target: Docker Swarm

The services are deployed to a Docker Swarm cluster, providing simple, built-in orchestration.

- **Multi-Node Cluster**: The inventory allows for defining manager and worker nodes, enabling high availability and resource distribution.
- **Overlay Networking**: A dedicated overlay network (`traefik-public`) is created to allow secure communication between all deployed services across different nodes.

## Deployment Process

When a user runs `task ansible:deploy:full`, the following happens:
1.  **Task Execution**: The `task` command in `Taskfile.yml` invokes the corresponding Ansible playbook.
2.  **Ansible Playbook**: The `ansible-playbook` command executes.
3.  **Inventory Parsing**: Ansible reads the `ansible/inventory/` to understand the target hosts.
4.  **Playbook Logic**: The `deploy/stacks.yml` playbook finds all `docker-compose.yml` files in the `stacks/` directories.
5.  **Stack Deployment**: For each compose file found, Ansible uses the `docker_stack` module to deploy it to the Docker Swarm manager. Variables from the `.env` file are injected into the services.
6.  **Swarm Orchestration**: Docker Swarm receives the stack definition and schedules the containers across the manager and worker nodes according to the service's configuration (e.g., placement constraints, replicas).
7.  **Service Discovery & Routing**: Once the services are running, Traefik (the reverse proxy) automatically detects them via Docker labels on the service definitions and configures routing and SSL certificates.

## Design Principles

1.  **Infrastructure as Code (IaC)**: The entire state of the homelab (hosts, services, configuration) is defined in version-controlled text files.
2.  **Simplicity over Complexity**: Docker Swarm and standard Docker Compose files are used for their simplicity and low learning curve compared to more complex orchestrators like Kubernetes.
3.  **Extensibility**: Adding a new service is as simple as creating a new subdirectory in `stacks/` with a `docker-compose.yml` file. No central registration is needed.
4.  **Separation of Concerns**:
    - `.env`: Holds secrets and instance-specific configuration.
    - `inventory/`: Defines the machine infrastructure.
    - `stacks/`: Defines the services to be run.
    - `playbooks/`: Defines the deployment logic.
