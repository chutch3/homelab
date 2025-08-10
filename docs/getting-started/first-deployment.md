# First Deployment

This guide walks you through your first deployment using different orchestration platforms. Choose the deployment type that best fits your needs.

## Choose Your Deployment Type

<div class="grid cards" markdown>

- :material-docker: **[Docker Compose](#docker-compose-deployment)**

    ---

    **Best for**: Single node, development, simple production setups

    **Pros**: Simple, widely supported, easy to debug

    **Cons**: Single point of failure, manual scaling

- :material-docker: **[Docker Swarm](#docker-swarm-deployment)**

    ---

    **Best for**: Multi-node clusters, high availability, load balancing

    **Pros**: Built-in orchestration, secrets management, rolling updates

    **Cons**: More complex setup, Docker-specific

- :material-kubernetes: **[Kubernetes](#kubernetes-deployment)**

    ---

    **Best for**: Large-scale deployments, enterprise environments

    **Pros**: Industry standard, advanced features, ecosystem

    **Cons**: Complex setup, resource overhead, steep learning curve

</div>

---

## Docker Compose Deployment

Docker Compose is the simplest way to get started and perfect for single-node deployments.

### Prerequisites

- Docker Engine 24.0+ with Docker Compose v2
- Domain with Cloudflare DNS
- Configured `.env` file

### Step 1: Enable Services

Choose which services you want to deploy:

```bash
# List available services
./selfhosted service list

# Enable specific services
./selfhosted service enable homepage actual

# Or use interactive selection
./selfhosted service interactive
```

### Step 2: Generate Deployment Files

```bash
# Generate all deployment files
./selfhosted service generate

# Verify generated files
ls -la generated/deployments/
```

This creates:
```
generated/deployments/
├── docker-compose.yaml     # Main compose file
└── docker-compose.override.yaml  # Environment-specific overrides
```

### Step 3: Review Generated Configuration

```yaml title="generated/deployments/docker-compose.yaml"
version: '3.8'

services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    container_name: homepage
    ports:
      - "3000:3000"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
    volumes:
      - ./data/homepage:/app/config
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
    networks:
      - selfhosted

  actual:
    image: actualbudget/actual-server:latest
    container_name: actual
    ports:
      - "5006:5006"
    environment:
      - ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB=20
    volumes:
      - ./data/actual:/app/data
    restart: unless-stopped
    networks:
      - selfhosted

  nginx:
    image: nginx:alpine
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./generated/nginx/templates:/etc/nginx/templates:ro
      - ./certs:/etc/nginx/certs:ro
      - ./nginx/conf.d:/etc/nginx/conf.d
    environment:
      - BASE_DOMAIN=yourdomain.com
    depends_on:
      - homepage
      - actual
    restart: unless-stopped
    networks:
      - selfhosted

networks:
  selfhosted:
    external: true
```

### Step 4: Create Docker Network

```bash
# Create the external network
docker network create selfhosted
```

### Step 5: Deploy Services

```bash
# Deploy all services
./selfhosted deploy compose up

# Or manually with docker compose
cd generated/deployments
docker compose up -d
```

### Step 6: Verify Deployment

```bash
# Check service status
docker compose ps

# View logs
docker compose logs

# Check specific service logs
docker compose logs homepage
docker compose logs actual
```

Expected output:
```
NAME      IMAGE                              COMMAND   SERVICE    STATUS    PORTS
actual    actualbudget/actual-server:latest  "..."     actual     Up        0.0.0.0:5006->5006/tcp
homepage  ghcr.io/gethomepage/homepage:latest "..."    homepage   Up        0.0.0.0:3000->3000/tcp
nginx     nginx:alpine                       "..."     nginx      Up        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### Step 7: Access Your Services

- **Homepage Dashboard**: `https://dashboard.yourdomain.com`
- **Actual Budget**: `https://budget.yourdomain.com`

### Management Commands

```bash
# Start services
./selfhosted deploy compose up

# Stop services
./selfhosted deploy compose down

# Restart specific service
./selfhosted deploy compose restart actual

# Update services
./selfhosted deploy compose pull
./selfhosted deploy compose up -d

# Scale service (if supported)
./selfhosted deploy compose scale actual=2

# View resource usage
docker stats
```

---

## Docker Swarm Deployment

Docker Swarm provides built-in orchestration for multi-node clusters with high availability.

### Prerequisites

- Multiple Docker nodes (manager + workers)
- Configured `config/machines.yml`
- Shared storage (NFS/GlusterFS) for persistent data

### Step 1: Initialize Swarm Cluster

On the manager node:

```bash
# Initialize swarm
docker swarm init --advertise-addr 192.168.1.10

# Get join token for workers
docker swarm join-token worker
```

On worker nodes:

```bash
# Join the swarm (use token from manager)
docker swarm join --token SWMTKN-1-... 192.168.1.10:2377
```

### Step 2: Setup Machine Configuration

```yaml title="config/machines.yml"
version: "1.0"

nodes:
  manager:
    hostname: "manager.local"
    ip: "192.168.1.10"
    role: "manager"
    ssh_user: "ubuntu"
    labels:
      - "node.type=manager"
      - "storage.type=ssd"

  worker1:
    hostname: "worker1.local"
    ip: "192.168.1.11"
    role: "worker"
    ssh_user: "ubuntu"
    labels:
      - "node.type=worker"
      - "storage.type=hdd"
```

### Step 3: Configure Services for Swarm

Enable services and generate Swarm stack:

```bash
# Enable services
./selfhosted service enable homepage actual

# Generate Swarm deployment
./selfhosted service generate

# Deploy to Swarm
./selfhosted deploy swarm deploy
```

### Step 4: Review Swarm Stack

```yaml title="generated/deployments/swarm-stack.yaml"
version: '3.8'

services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    ports:
      - "3000:3000"
    environment:
      - PUID=1000
      - PGID=1000
    volumes:
      - homepage_data:/app/config
      - /var/run/docker.sock:/var/run/docker.sock:ro
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    networks:
      - selfhosted

  actual:
    image: actualbudget/actual-server:latest
    ports:
      - "5006:5006"
    environment:
      - ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB=20
    volumes:
      - actual_data:/app/data
    deploy:
      mode: replicated
      replicas: 2  # High availability
      placement:
        constraints:
          - node.type == worker
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
    networks:
      - selfhosted

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - nginx_config:/etc/nginx/templates:ro
      - nginx_certs:/etc/nginx/certs:ro
    deploy:
      mode: global  # Run on all nodes
      placement:
        constraints:
          - node.role == worker
    networks:
      - selfhosted

volumes:
  homepage_data:
    driver: nfs
    driver_opts:
      share: "192.168.1.100:/volume1/homepage"

  actual_data:
    driver: nfs
    driver_opts:
      share: "192.168.1.100:/volume1/actual"

  nginx_config:
    driver: local

  nginx_certs:
    driver: local

networks:
  selfhosted:
    driver: overlay
    attachable: true

secrets:
  cf_token:
    external: true
```

### Step 5: Deploy Stack

```bash
# Create secrets
echo "your_cf_token" | docker secret create cf_token -

# Deploy the stack
docker stack deploy -c generated/deployments/swarm-stack.yaml selfhosted

# Verify deployment
docker stack services selfhosted
docker stack ps selfhosted
```

### Step 6: Swarm Management

```bash
# List stacks
docker stack ls

# Scale service
docker service scale selfhosted_actual=3

# Update service
docker service update --image actualbudget/actual-server:latest selfhosted_actual

# Rolling update
docker service update --update-parallelism 1 --update-delay 10s selfhosted_actual

# Remove stack
docker stack rm selfhosted
```

---

## Kubernetes Deployment

Kubernetes provides enterprise-grade orchestration with advanced features.

!!! warning "Kubernetes Support"
    Kubernetes support is currently in development. This section shows the planned implementation.

### Prerequisites

- Kubernetes cluster (k3s, k8s, EKS, GKE, AKS)
- kubectl configured
- Helm 3.x (optional)
- Ingress controller (nginx, traefik)
- Cert-manager for SSL

### Step 1: Setup Kubernetes Cluster

=== "k3s (Lightweight)"

    ```bash
    # Install k3s on master
    curl -sfL https://get.k3s.io | sh -s - server --cluster-init

    # Get node token
    sudo cat /var/lib/rancher/k3s/server/node-token

    # Join additional nodes
    curl -sfL https://get.k3s.io | K3S_URL=https://master-ip:6443 K3S_TOKEN=token sh -
    ```

=== "kubeadm (Full Kubernetes)"

    ```bash
    # Initialize cluster
    sudo kubeadm init --pod-network-cidr=10.244.0.0/16

    # Configure kubectl
    mkdir -p $HOME/.kube
    sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config

    # Install CNI plugin
    kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
    ```

### Step 2: Install Required Components

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Install nginx ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# Verify installations
kubectl get pods -n cert-manager
kubectl get pods -n ingress-nginx
```

### Step 3: Generate Kubernetes Manifests

```bash
# Enable services
./selfhosted service enable homepage actual

# Generate Kubernetes manifests
./selfhosted service generate --platform kubernetes

# Review generated files
ls -la generated/kubernetes/
```

This creates:
```
generated/kubernetes/
├── namespace.yaml
├── configmaps/
├── secrets/
├── deployments/
├── services/
├── ingresses/
└── persistent-volumes/
```

### Step 4: Review Generated Manifests

```yaml title="generated/kubernetes/deployments/actual.yaml"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: actual
  namespace: selfhosted
  labels:
    app: actual
    component: finance
spec:
  replicas: 2
  selector:
    matchLabels:
      app: actual
  template:
    metadata:
      labels:
        app: actual
    spec:
      containers:
      - name: actual
        image: actualbudget/actual-server:latest
        ports:
        - containerPort: 5006
          name: http
        env:
        - name: ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB
          value: "20"
        volumeMounts:
        - name: actual-data
          mountPath: /app/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: 5006
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 5006
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: actual-data
        persistentVolumeClaim:
          claimName: actual-data-pvc
```

```yaml title="generated/kubernetes/services/actual.yaml"
apiVersion: v1
kind: Service
metadata:
  name: actual
  namespace: selfhosted
  labels:
    app: actual
spec:
  selector:
    app: actual
  ports:
  - name: http
    port: 5006
    targetPort: 5006
  type: ClusterIP
```

```yaml title="generated/kubernetes/ingresses/actual.yaml"
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: actual
  namespace: selfhosted
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - budget.yourdomain.com
    secretName: actual-tls
  rules:
  - host: budget.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: actual
            port:
              number: 5006
```

### Step 5: Deploy to Kubernetes

```bash
# Deploy all manifests
./selfhosted deploy kubernetes apply

# Or manually apply
kubectl apply -R -f generated/kubernetes/

# Verify deployment
kubectl get pods -n selfhosted
kubectl get services -n selfhosted
kubectl get ingresses -n selfhosted
```

### Step 6: Kubernetes Management

```bash
# Scale deployment
kubectl scale deployment actual --replicas=3 -n selfhosted

# Rolling update
kubectl set image deployment/actual actual=actualbudget/actual-server:v2 -n selfhosted

# Check rollout status
kubectl rollout status deployment/actual -n selfhosted

# Rollback if needed
kubectl rollout undo deployment/actual -n selfhosted

# View logs
kubectl logs -f deployment/actual -n selfhosted

# Port forward for debugging
kubectl port-forward service/actual 5006:5006 -n selfhosted
```

---

## Troubleshooting Common Issues

### Docker Compose Issues

??? question "Services won't start?"

    ```bash
    # Check service logs
    docker compose logs service-name

    # Check Docker daemon
    systemctl status docker

    # Verify network
    docker network ls
    docker network inspect selfhosted
    ```

??? question "Port conflicts?"

    ```bash
    # Check what's using the port
    sudo netstat -tulpn | grep :80
    sudo lsof -i :80

    # Stop conflicting services
    sudo systemctl stop apache2
    sudo systemctl stop nginx
    ```

### Docker Swarm Issues

??? question "Node won't join swarm?"

    ```bash
    # Check connectivity
    telnet manager-ip 2377

    # Regenerate join token
    docker swarm join-token worker

    # Check firewall ports
    sudo ufw allow 2377/tcp  # Swarm management
    sudo ufw allow 7946/tcp  # Container network discovery
    sudo ufw allow 4789/udp  # Container ingress network
    ```

??? question "Service won't deploy?"

    ```bash
    # Check service logs
    docker service logs service-name

    # Check placement constraints
    docker service inspect service-name

    # List available nodes
    docker node ls
    ```

### Kubernetes Issues

??? question "Pods stuck in Pending?"

    ```bash
    # Check events
    kubectl describe pod pod-name -n selfhosted

    # Check node resources
    kubectl describe nodes

    # Check persistent volumes
    kubectl get pv,pvc -n selfhosted
    ```

??? question "Ingress not working?"

    ```bash
    # Check ingress controller
    kubectl get pods -n ingress-nginx

    # Check ingress configuration
    kubectl describe ingress actual -n selfhosted

    # Check DNS resolution
    nslookup budget.yourdomain.com
    ```

[Next: Learn about service management →](../user-guide/service-management.md)
