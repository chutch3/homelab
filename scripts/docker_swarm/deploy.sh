#!/bin/bash
set -euo pipefail

# Docker Swarm Deployment Script
# Handles deployment of services to Docker Swarm cluster

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)
_DEPLOY_SCRIPT_DIR="$SCRIPT_DIR"  # Save deploy.sh's SCRIPT_DIR
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
STACKS_DIR="$PROJECT_ROOT/stacks"
APPS_DIR="$STACKS_DIR/apps"
REVERSE_PROXY_DIR="$STACKS_DIR/reverse-proxy"
MONITORING_DIR="$STACKS_DIR/monitoring"
DNS_DIR="$STACKS_DIR/dns"
NETWORK_NAME="traefik-public"
MACHINES_FILE="$PROJECT_ROOT/machines.yaml"

# Source common utilities (they may overwrite SCRIPT_DIR)
# shellcheck source=../common/ssh.sh
source "$_DEPLOY_SCRIPT_DIR/../common/ssh.sh"
# shellcheck source=../common/machine.sh
source "$_DEPLOY_SCRIPT_DIR/../common/machine.sh"
# shellcheck source=../common/dns.sh
source "$_DEPLOY_SCRIPT_DIR/../common/dns.sh"
SCRIPT_DIR="$_DEPLOY_SCRIPT_DIR"  # Restore deploy.sh's SCRIPT_DIR
# shellcheck source=cluster.sh
source "$SCRIPT_DIR/cluster.sh"
# shellcheck source=monitoring.sh
source "$SCRIPT_DIR/monitoring.sh"

# Colors
COLOR_RESET='\033[0m'
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'
COLOR_BOLD='\033[1m'

log() {
  echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"
}
log_success() {
  echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $1"
}
log_warn() {
  echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"
}
log_error() {
  echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" >&2
}
log_header() {
  echo -e "
${COLOR_BOLD}--- $1 ---${COLOR_RESET}"
}

check_configs() {
  # Check that required files exist
  if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_error ".env file not found. Please copy .env.example to .env and configure it."
    exit 1
  fi

  if [ ! -f "$MACHINES_FILE" ]; then
    log_error "machines.yaml not found at $MACHINES_FILE"
    exit 1
  fi
}

# --- ASCII Art Banner ---
show_banner() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}"
  cat << 'EOF'
 ███████ ███████ ██      ███████ ██   ██  ██████  ███████ ████████ ███████ ██████      ███████ ██   ██
 ██      ██      ██      ██      ██   ██ ██    ██ ██         ██    ██      ██   ██     ██      ██   ██
 ███████ █████   ██      █████   ███████ ██    ██ ███████    ██    █████   ██   ██     ███████ ███████
      ██ ██      ██      ██      ██   ██ ██    ██      ██    ██    ██      ██   ██          ██ ██   ██
 ███████ ███████ ███████ ██      ██   ██  ██████  ███████    ██    ███████ ██████  ██  ███████ ██   ██

EOF
  echo -e "${COLOR_GREEN}"
  cat << 'EOF'
   🏠 HOMELAB DEPLOYMENT AUTOMATION 🚀
   ═══════════════════════════════════════
   Docker Swarm • Container Management
   Network Configuration • SSL Automation
   Multi-Node Orchestration • Self-Healing
   ═══════════════════════════════════════

EOF
  echo -e "${COLOR_RESET}"
}

show_compact_banner() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}🏠 SELFHOSTED HOMELAB 🚀${COLOR_RESET} ${COLOR_GREEN}Deploy • Manage • Scale${COLOR_RESET}"
  echo -e "${COLOR_YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${COLOR_RESET}"
}

deploy_stack() {
  local name="$1"
  local compose_file="$2"
  local max_retries=5
  local retry_delay=10 # in seconds
  local attempt=0
  local output

  log "Deploying stack: ${COLOR_YELLOW}$name${COLOR_RESET}"

  while (( attempt < max_retries )); do
    attempt=$((attempt + 1))

    # Step 1: Validate compose file first
    log "Validating compose file for stack '$name'..."
    local config_output
    if ! config_output=$(cd "$PROJECT_ROOT" && set -a && source .env && set +a && docker stack config -c "$compose_file" 2>&1); then
      log_error "Compose file validation failed for stack '$name':"
      echo "$config_output" | head -5 | while IFS= read -r line; do
        echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
      done
      if (( attempt < max_retries )); then
        log_warn "Retrying validation in $retry_delay seconds... (Attempt ${attempt}/${max_retries})"
        sleep "$retry_delay"
        continue
      else
        return 1
      fi
    fi

    # Step 2: Deploy with better error handling
    log "Deploying validated configuration for stack '$name'..."
    local deploy_exit_code
    output=$(cd "$PROJECT_ROOT" && set -a && source .env && set +a && echo "$config_output" | timeout 120s docker stack deploy --detach=false --resolve-image never -c - "$name" 2>&1)
    deploy_exit_code=$?

    # Step 3: Check deployment result more carefully
    if [ $deploy_exit_code -eq 0 ]; then
      # Double-check that stack actually exists and has services
      sleep 3 # Give Docker a moment to register the stack
      local stack_exists service_count
      stack_exists=$(docker stack ls --format "{{.Name}}" | grep -c "^${name}$" || true)
      service_count=$(docker stack services "$name" 2>/dev/null | wc -l || echo "0")

      if [ "$stack_exists" -eq 1 ] && [ "$service_count" -gt 0 ]; then
        log_success "Stack '${COLOR_YELLOW}$name${COLOR_RESET}' deployed successfully."

        log "Displaying service placement..."
        sleep 2 # Give swarm a moment to update
        docker stack ps "$name" --filter "desired-state=running" --format "{{.Name}} → {{.Node}}" 2>/dev/null | while read -r placement; do
          echo -e "${COLOR_YELLOW}$placement${COLOR_RESET}"
        done

        return 0
      else
        log_warn "Deployment command succeeded but stack validation failed (stack_exists=$stack_exists, services=$service_count)"
      fi
    else
      log_warn "Deployment command failed with exit code $deploy_exit_code"
    fi

    # If we are here, the command failed.
    if (( attempt < max_retries )); then
      log_warn "Deployment of '${COLOR_YELLOW}$name${COLOR_RESET}' failed. Retrying in $retry_delay seconds... (Attempt ${attempt}/${max_retries})"
    else
      log_error "Failed to deploy stack '${COLOR_YELLOW}$name${COLOR_RESET}' after $max_retries attempts."
    fi

    # Show meaningful service errors grouped by type (only if stack exists)
    if docker stack ls --format "{{.Name}}" | grep -q "^${name}$"; then
        log_error "Service task errors for stack '$name':"
        sleep 2

        # Show unique meaningful errors (exclude generic exit codes)
        local meaningful_errors
        meaningful_errors=$(docker stack ps "$name" --no-trunc --filter "desired-state=shutdown" --format "{{.Name}}: {{.Error}}" 2>/dev/null | \
        grep -v "task: non-zero exit" | \
        grep -v "^[^:]*:[[:space:]]*$" | \
        sort -u | \
        head -10)

        if [[ -n "$meaningful_errors" ]]; then
            echo "$meaningful_errors" | while IFS= read -r line; do
                echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
            done
        else
            log_error "No specific error details available (stack may be initializing)"
        fi

        # Show error summary counts
        local error_summary
        error_summary=$(docker stack ps "$name" --filter "desired-state=shutdown" --format "{{.Error}}" 2>/dev/null | \
        sort | uniq -c | sort -nr | head -5)

        if [[ -n "$error_summary" ]]; then
            log_error "Error summary (top issues):"
            echo "$error_summary" | while IFS= read -r line; do
                echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
            done
        fi
    else
        log_error "Stack '$name' not found - may be initializing or deployment command failed"
    fi

    # Show deployment command output for debugging
    log_error "Deployment output analysis:"
    if [[ -n "$output" ]]; then
        # Show last few lines of output for context
        echo "$output" | tail -10 | while IFS= read -r line; do
            echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
        done

        # Show specific deployment failures
        local deploy_failures
        deploy_failures=$(echo "$output" | \
        grep -i "failed\|error\|invalid\|denied\|timeout" | \
        grep -v "overall progress:" | \
        grep -v "verify:" | \
        sort -u | \
        head -5)

        if [[ -n "$deploy_failures" ]]; then
            log_error "Specific deployment issues found:"
            echo "$deploy_failures" | while IFS= read -r line; do
                echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
            done
        fi
    else
        log_error "No deployment output captured"
    fi

    # Additional debugging info
    log_error "Debugging info:"
    echo -e "${COLOR_RED}    - Exit code: $deploy_exit_code${COLOR_RESET}" >&2
    echo -e "${COLOR_RED}    - Timeout: 120s${COLOR_RESET}" >&2
    echo -e "${COLOR_RED}    - Attempt: ${attempt}/${max_retries}${COLOR_RESET}" >&2

    if (( attempt < max_retries )); then
        sleep "$retry_delay"
    fi
  done

  return 1
}



deploy_cluster() {
  local skip_apps=()
  local only_apps=()
  local skip_infra=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        show_banner
        echo -e "${COLOR_BOLD}${COLOR_GREEN}USAGE:${COLOR_RESET} $0 deploy [options]"
        echo ""
        echo -e "${COLOR_BOLD}${COLOR_BLUE}OPTIONS:${COLOR_RESET}"
        echo -e "  ${COLOR_YELLOW}--skip-infra${COLOR_RESET}         Skip infrastructure setup (faster app updates)"
        echo -e "  ${COLOR_YELLOW}--skip-apps <apps>${COLOR_RESET}    Comma-separated list of apps to skip"
        echo -e "  ${COLOR_YELLOW}--only-apps <apps>${COLOR_RESET}    Comma-separated list of apps to deploy (only these)"
        echo -e "  ${COLOR_YELLOW}--help, -h${COLOR_RESET}           Show this help message"
        echo ""
        echo -e "${COLOR_BOLD}${COLOR_BLUE}EXAMPLES:${COLOR_RESET}"
        echo -e "  ${COLOR_GREEN}$0 deploy${COLOR_RESET}                              # Full deployment (infrastructure + apps)"
        echo -e "  ${COLOR_GREEN}$0 deploy --skip-infra${COLOR_RESET}                       # Quick app updates only"
        echo -e "  ${COLOR_GREEN}$0 deploy --skip-apps homeassistant,emby${COLOR_RESET}       # Skip specific apps"
        echo -e "  ${COLOR_GREEN}$0 deploy --only-apps sonarr,radarr${COLOR_RESET}            # Deploy only specific apps"
        echo -e "  ${COLOR_GREEN}$0 deploy --skip-infra --only-apps homepage${COLOR_RESET}    # Update one app quickly"
        exit 0
        ;;
      --skip-infra)
        skip_infra=true
        shift
        ;;
      --skip-apps)
        if [[ -z "${2:-}" ]]; then
          log_error "--skip-apps requires an argument (comma-separated list of apps)"
          echo "Usage: deploy --skip-apps app1,app2,app3"
          exit 1
        fi
        IFS=',' read -r -a skip_apps <<< "$2"
        shift 2
        ;;
      --only-apps)
        if [[ -z "${2:-}" ]]; then
          log_error "--only-apps requires an argument (comma-separated list of apps)"
          echo "Usage: deploy --only-apps app1,app2,app3"
          exit 1
        fi
        IFS=',' read -r -a only_apps <<< "$2"
        shift 2
        ;;
      *)
        log_error "Unknown option for deploy command: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
    esac
  done

  check_configs
  source "$PROJECT_ROOT/.env"
  source "$PROJECT_ROOT/scripts/common/machine.sh"

  # Orchestrator-agnostic pattern: skip infrastructure setup if --skip-infra is set
  # This pattern applies to all orchestrators (Swarm, Kubernetes, etc.)
  if [[ "$skip_infra" == "false" ]]; then
    log_header "PHASE 1: MACHINE & SWARM SETUP"
    log "Setting up SSH for all machines..."
    machines_setup_ssh
    log "Checking for cifs-utils on all nodes..."
    machines_check_cifs_utils

    initialize_swarm_cluster "$MACHINES_FILE"

    log "Configuring Docker daemon metrics on all nodes..."
    if configure_all_nodes "$MACHINES_FILE"; then
      log_success "Docker daemon metrics configured on all nodes"
    else
      log_warn "Failed to configure metrics on some nodes, but deployment continues"
    fi

    log_header "PHASE 2: CORE INFRASTRUCTURE"
    log "Ensuring overlay network '${COLOR_YELLOW}${NETWORK_NAME}${COLOR_RESET}' exists..."
    if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
      log "Network not found. Creating..."
      docker network create --driver=overlay --attachable "${NETWORK_NAME}"
      log_success "Network '${COLOR_YELLOW}${NETWORK_NAME}${COLOR_RESET}' created."
    else
      log "Network '${COLOR_YELLOW}${NETWORK_NAME}${COLOR_RESET}' already exists."
    fi

    # Deploy DNS stack first to ensure all services have DNS records
    if [ -f "$DNS_DIR/docker-compose.yml" ]; then
      deploy_stack "dns" "$DNS_DIR/docker-compose.yml"
      # Wait for DNS server to be ready, then configure DNS records
      log "Configuring DNS records for local services..."
      sleep 10  # Give DNS server time to start

      # Get manager machine IP for DNS server URL
      if MANAGER_IP=$(machines_get_ip "manager" 2>/dev/null); then
        export DNS_SERVER_URL="http://${MANAGER_IP}:5380"
        configure_dns_records || log_warn "DNS records configuration failed, but deployment continues"
      else
        log_warn "Could not determine manager IP, skipping DNS configuration"
      fi
    else
      log_warn "DNS stack not found, skipping."
    fi
  else
    log "Skipping infrastructure setup (--skip-infra mode)"
  fi

  deploy_stack "reverse-proxy" "$REVERSE_PROXY_DIR/docker-compose.yml"

  if [ -f "$MONITORING_DIR/docker-compose.yml" ]; then
    deploy_stack "monitoring" "$MONITORING_DIR/docker-compose.yml"
  else
    log_warn "Monitoring stack not found, skipping."
  fi

  log_header "PHASE 3: APPLICATION DEPLOYMENT"
  local pids=()
  for app_path in "$APPS_DIR"/*; do
    if [ -d "$app_path" ] && [ -f "$app_path/docker-compose.yml" ]; then
      local stack_name
      stack_name="$(basename "$app_path")"

      if [ ${#only_apps[@]} -gt 0 ] && [[ ! " ${only_apps[*]} " =~  ${stack_name}  ]]; then
        continue
      fi
      if [[ " ${skip_apps[*]} " =~  ${stack_name}  ]]; then
        log_warn "Skipping app stack as requested: $stack_name"
        continue
      fi

      deploy_stack "$stack_name" "$app_path/docker-compose.yml" &
      pids+=($!)
    fi
  done

  log "Waiting for all app deployments to complete..."
  local deployment_failed_count=0
  local deployed_stacks=()

  # Wait for all deployment processes
  for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
      deployment_failed_count=$((deployment_failed_count + 1))
    fi
  done

  # Collect all deployed stack names for verification
  for app_path in "$APPS_DIR"/*; do
    if [ -d "$app_path" ] && [ -f "$app_path/docker-compose.yml" ]; then
      local stack_name
      stack_name="$(basename "$app_path")"

      if [ ${#only_apps[@]} -gt 0 ] && [[ ! " ${only_apps[*]} " =~  ${stack_name}  ]]; then
        continue
      fi
      if [[ " ${skip_apps[*]} " =~  ${stack_name}  ]]; then
        continue
      fi

      deployed_stacks+=("$stack_name")
    fi
  done

  # Verify final service state regardless of deployment process results
  log "Verifying final service states..."
  local final_failed_count=0
  for stack_name in "${deployed_stacks[@]}"; do
    local total_services
    total_services=$(docker stack services "$stack_name" --format "{{.Replicas}}" 2>/dev/null | wc -l)

    if [ "$total_services" -eq 0 ]; then
      log_error "Stack '$stack_name' has no services running"
      final_failed_count=$((final_failed_count + 1))
    else
      # Check if all services have desired replicas running
      local all_healthy=true
      while IFS= read -r replica_info; do
        if [[ "$replica_info" == *"0/"* ]]; then
          all_healthy=false
          break
        fi
      done < <(docker stack services "$stack_name" --format "{{.Name}}: {{.Replicas}}" 2>/dev/null)

      if [ "$all_healthy" = true ]; then
        log_success "Stack '$stack_name' is healthy"
      else
        log_error "Stack '$stack_name' has unhealthy services"
        final_failed_count=$((final_failed_count + 1))
      fi
    fi
  done

  # Report final results based on actual service state
  if [ "$final_failed_count" -gt 0 ]; then
    log_error "$final_failed_count stack(s) are not running properly. Please review service logs."
    if [ "$deployment_failed_count" -gt 0 ]; then
      log_error "Note: $deployment_failed_count deployment process(es) also failed during initial deployment."
    fi
  else
    log_success "All application stacks are running successfully."
    if [ "$deployment_failed_count" -gt 0 ]; then
      log_warn "Note: $deployment_failed_count deployment process(es) failed initially but services recovered successfully."
    fi
  fi

  log_header "PHASE 4: CLUSTER MONITORING"
  log "Running cluster status monitor..."
  monitor_swarm_cluster

  log_header "DEPLOYMENT COMPLETE"
  log_success "All stacks deployed!"
}

# --- Main Entrypoint ---

main() {
  deploy_cluster "$@"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
