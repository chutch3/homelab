#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$(realpath "$0")")/../.." && pwd)"

# Source SSH functions if available
if [ -f "$PROJECT_ROOT/scripts/common/ssh.sh" ]; then
  source "$PROJECT_ROOT/scripts/common/ssh.sh"
fi

# Source DNS configuration functions if available
if [ -f "$PROJECT_ROOT/scripts/common/dns.sh" ]; then
  source "$PROJECT_ROOT/scripts/common/dns.sh"
fi

# Define all homelab volumes that need cleanup
HOMELAB_VOLUMES=(
  "budget" "ssl_certs" "cryptpad" "deluge" "torrents" "usenet" "all_data"
  "emby" "homeassistant" "homepage" "librechat_meilisearch" "librechat_mongodb"
  "photoprism" "prowlarr" "qbittorrent" "radarr" "sonarr" "grafana_dashboards"
  "grafana_data" "prometheus_data" "dns-config"
)

# Initialize machines configuration
init_machines_config() {
  MACHINES_FILE="${1:-machines.yaml}"

  if ! [ -f "$MACHINES_FILE" ]; then
    echo "Error: $MACHINES_FILE not found!"
    exit 1
  fi

  # Extract user@IP for all machines using machines functions
  # Use IP addresses instead of hostnames since DNS will be unavailable during nuke
  NODES=()
  local machine_keys
  machine_keys="$(machines_parse all)"
  for machine_key in $machine_keys; do
    local machine_ip
    local ssh_user
    machine_ip=$(machines_get_ip "$machine_key")
    ssh_user=$(machines_get_ssh_user "$machine_key")
    if [ "$ssh_user" = "null" ]; then
      ssh_user=${USER}
    fi
    NODES+=("$ssh_user@$machine_ip")
  done
}

# Function to discover volumes for a stack across all nodes
# This finds orphaned volumes that may exist on nodes where the service used to run
discover_stack_volumes_on_node() {
  local node="$1"
  local stack_name="$2"

  ssh_key_auth "$node" "docker volume ls --filter 'name=${stack_name}' --format '{{.Name}}' 2>/dev/null" || true
}

# Function to teardown a specific stack and clean its volumes on all nodes
teardown_stack() {
  local stack_name="$1"
  local dry_run="${2:-false}"

  if [ "$dry_run" = true ]; then
    echo "=== DRY RUN MODE ==="
    echo "Would perform the following actions:"
    echo ""
  fi

  # Remove the stack first
  if [ "$dry_run" = true ]; then
    echo "Would remove stack: $stack_name"
  else
    echo "Removing stack: $stack_name"
    docker stack rm "$stack_name" 2>/dev/null || echo "Stack not found: $stack_name"
    echo "Waiting for stack to be removed..."
    sleep 5
  fi
  echo ""

  # Clean volumes on all nodes (including orphaned ones)
  echo "Searching for volumes on all nodes..."
  for node in "${NODES[@]}"; do
    echo "Checking node: $node"

    local volumes
    volumes=$(discover_stack_volumes_on_node "$node" "$stack_name")

    if [ -z "$volumes" ]; then
      echo "  No volumes found"
      continue
    fi

    while IFS= read -r vol; do
      [ -z "$vol" ] && continue

      if [ "$dry_run" = true ]; then
        echo "  Would remove volume: $vol"
      else
        echo "  Removing volume: $vol"
        ssh_key_auth "$node" "docker volume rm $vol" || echo "    Failed to remove $vol (may be in use)"
      fi
    done <<< "$volumes"
  done

  if [ "$dry_run" = true ]; then
    echo ""
    echo "=== DRY RUN COMPLETE ==="
    echo "No changes were made. Run without --dry-run to execute."
  else
    echo ""
    echo "Stack teardown completed: $stack_name"
  fi
}

# Function to cleanup DNS records and zone
cleanup_dns_records() {
  echo "Cleaning up DNS records..."

  # Source environment variables if available
  if [ -f "$PROJECT_ROOT/.env" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
  fi

  # Check if DNS server is running and accessible
  local dns_server_ip="${DNS_SERVER_IP:-$(yq '.machines | to_entries[] | select(.value.role == "manager") | .value.ip // "127.0.0.1"' "$MACHINES_FILE" | tr -d '"')}"

  if curl -s --max-time 5 "http://${dns_server_ip}:5380/api/user/login" > /dev/null 2>&1; then
    echo "DNS server accessible, attempting to clear records..."

    # Get DNS token if possible
    local dns_token
    if dns_token=$(get_dns_token 2>/dev/null); then
      export DNS_TOKEN="$dns_token"

      # Delete the entire DNS zone if BASE_DOMAIN is set
      local domain="${BASE_DOMAIN:-diyhub.dev}"
      echo "Deleting DNS zone: $domain"

      curl -s -X POST "http://${dns_server_ip}:5380/api/zones/delete" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "token=${DNS_TOKEN}" \
        -d "zone=${domain}" > /dev/null 2>&1 || echo "Failed to delete DNS zone (may not exist)"

      echo "DNS zone cleanup completed"
    else
      echo "Could not authenticate with DNS server, skipping record cleanup"
    fi
  else
    echo "DNS server not accessible, skipping DNS cleanup"
  fi
}

# Main execution function
main() {
  local stack_name=""
  local dry_run=false
  local machines_file="machines.yaml"

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --stack)
        stack_name="$2"
        shift 2
        ;;
      --dry-run)
        dry_run=true
        shift
        ;;
      -c|--config)
        machines_file="$2"
        shift 2
        ;;
      *)
        # Assume it's the machines file for backward compatibility
        machines_file="$1"
        shift
        ;;
    esac
  done

  # Initialize configuration
  init_machines_config "$machines_file"

  # If --stack is specified, do stack-specific teardown
  if [ -n "$stack_name" ]; then
    teardown_stack "$stack_name" "$dry_run"
    return 0
  fi

  # Validate --dry-run only works with --stack
  if [ "$dry_run" = true ]; then
    echo "Error: --dry-run is only supported with --stack option"
    exit 1
  fi

  # 1. Clean up DNS records first (while DNS server is still running)
  cleanup_dns_records

  # 2. Remove all stacks (on manager)
  echo "Removing all stacks..."
  for stack in $(docker stack ls --format '{{.Name}}'); do
    docker stack rm "$stack"
  done

  sleep 5

  # 3. Remove all custom overlay networks (on manager)
  echo "Removing custom overlay networks..."
  for net in $(docker network ls --filter driver=overlay --format '{{.Name}}' | grep -v ingress); do
    docker network rm "$net"
  done

  sleep 5

  # 4. Remove homelab volumes on all nodes
  echo "Removing homelab volumes on nodes..."
  for node in "${NODES[@]}"; do
    for vol in "${HOMELAB_VOLUMES[@]}"; do
      if ssh_key_auth "$node" "docker volume inspect $vol &>/dev/null"; then
        ssh_key_auth "$node" "docker volume rm $vol" || true
      fi
    done
  done

  sleep 5

  # 5. Remove all nodes from the manager (except self)
  echo "Removing all nodes from the manager..."
  SELF_ID=$(docker info -f '{{.Swarm.NodeID}}' 2>/dev/null || echo "")
  if [ -n "$SELF_ID" ]; then
    for node in $(docker node ls --format '{{.ID}}'); do
      if [[ "$node" != "$SELF_ID" ]]; then
        docker node rm --force "$node" || true
      fi
    done
  fi

  sleep 5

  # 6. SSH into each node and force leave the swarm
  echo "Forcing all nodes to leave the swarm..."
  for node in "${NODES[@]}"; do
    echo "Cleaning node: $node"
    ssh_key_auth "$node" "docker swarm leave --force || true"
  done

  # 7. Leave the swarm on the current node (manager)
  echo "Leaving the swarm on the manager..."
  docker swarm leave --force || true

  echo "Swarm cluster and all nodes have been cleaned up."
}

# Only run main execution if not being sourced for testing
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  main "$@"
fi
