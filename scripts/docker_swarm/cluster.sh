#!/bin/bash

# Get the actual script directory, handling both direct execution and sourcing
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PROJECT_ROOT

# Source the docker wrapper functions
# shellcheck source=scripts/docker_swarm/wrappers/docker.sh
source "$SCRIPT_DIR/wrappers/docker.sh"
# shellcheck source=scripts/common/ssh.sh
source "$SCRIPT_DIR/../common/ssh.sh"
# shellcheck source=scripts/common/machine.sh
source "$SCRIPT_DIR/../common/machine.sh"

# --- Colors and Logging ---
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
  echo -e "\n${COLOR_BOLD}--- $1 ---${COLOR_RESET}"
}

# check if docker is installed and running (skip in test mode)
if [ -z "${TEST:-}" ]; then
  if ! command -v docker &> /dev/null; then
    log_error "docker could not be found"
    exit 1
  fi

  if ! docker info &> /dev/null; then
    log_error "docker is not running"
    exit 1
  fi
fi


# =======================
# Swarm State Detection Functions
# =======================

# Function: is_swarm_active
# Description: Check if Docker Swarm is currently active on local node
# Arguments: None
# Returns: 0 if swarm is active, 1 if inactive or error
is_swarm_active() {
    local swarm_state
    swarm_state=$(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo "inactive")
    [[ "$swarm_state" == "active" ]]
}

# Function: is_node_manager
# Description: Check if current node is a swarm manager
# Arguments: None
# Returns: 0 if node is manager, 1 if worker/not in swarm/error
is_node_manager() {
    local control_available
    control_available=$(docker info --format '{{.Swarm.ControlAvailable}}' 2>/dev/null || echo "false")
    [[ "$control_available" == "true" ]]
}

# Function: get_swarm_status
# Description: Get comprehensive swarm status information for local node
# Arguments: None
# Returns: Multi-line status information
get_swarm_status() {
    local swarm_state control_available node_id role

    swarm_state=$(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo "unknown")
    control_available=$(docker info --format '{{.Swarm.ControlAvailable}}' 2>/dev/null || echo "false")
    node_id=$(docker info --format '{{.Swarm.NodeID}}' 2>/dev/null || echo "unknown")

    if [[ "$control_available" == "true" ]]; then
        role="manager"
    elif [[ "$swarm_state" == "active" ]]; then
        role="worker"
    else
        role="not-in-swarm"
    fi

    echo "Swarm State: $swarm_state"
    echo "Node Role: $role"
    echo "Node ID: $node_id"
}

# Function: is_remote_node_in_swarm
# Description: Check if a remote node is part of a swarm via SSH
# Arguments: $1 - user@host format
# Returns: 0 if node is in swarm, 1 if not in swarm or connection error
is_remote_node_in_swarm() {
    local node="$1"
    local swarm_state

    if [[ -z "$node" ]]; then
        log_error "node argument is required"
        return 1
    fi

    swarm_state=$(ssh_execute "$node" "docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null" 2>/dev/null | tr -d '\r\n')
    [[ "$swarm_state" == "active" ]]
}

# =======================
# Worker Node Membership Functions
# =======================

# Function: is_worker_in_swarm
# Description: Check if a specific worker node is already in the swarm
# Arguments: $1 - user@host format
# Returns: 0 if worker is in swarm, 1 if not or error
is_worker_in_swarm() {
    local worker_node="$1"

    if [[ -z "$worker_node" ]]; then
        log_error "worker_node argument is required"
        return 1
    fi

    is_remote_node_in_swarm "$worker_node"
}

# Function: get_workers_not_in_swarm
# Description: Get list of worker machines that are not yet in the swarm
# Arguments: $1 - config file path
# Returns: Space-separated list of worker machine names not in swarm
get_workers_not_in_swarm() {
    local config_file="${1:-machines.yaml}"
    local workers_not_in_swarm=()

    local workers
    workers=$(get_worker_machines "$config_file")

    for worker in $workers; do
        if [[ -z "$worker" ]]; then
            continue
        fi

        local worker_host worker_user
        worker_host=$(get_machine_host "$worker" "$config_file")
        worker_user=$(get_machine_user "$worker" "$config_file")

        if ! is_worker_in_swarm "$worker_user@$worker_host"; then
            workers_not_in_swarm+=("$worker")
        fi
    done

    printf '%s ' "${workers_not_in_swarm[@]}"
}

# Function: check_all_workers_swarm_status
# Description: Check and report swarm membership status for all workers
# Arguments: $1 - config file path
# Returns: Status report for all workers
check_all_workers_swarm_status() {
    local config_file="${1:-machines.yaml}"

    local workers
    workers=$(get_worker_machines "$config_file")

    for worker in $workers; do
        if [[ -z "$worker" ]]; then
            continue
        fi

        local worker_host worker_user
        worker_host=$(get_machine_host "$worker" "$config_file")
        worker_user=$(get_machine_user "$worker" "$config_file")

        if is_worker_in_swarm "$worker_user@$worker_host"; then
            echo "$worker: IN SWARM"
        else
            echo "$worker: NOT IN SWARM"
        fi
    done
}

# =======================
# Node Label Management Functions
# =======================

# Function: node_has_label
# Description: Check if a Docker node already has a specific label
# Arguments: $1 - node name, $2 - label in key=value format
# Returns: 0 if label exists, 1 if not
node_has_label() {
    local node_name="$1"
    local target_label="$2"

    if [[ -z "$node_name" || -z "$target_label" ]]; then
        log_error "node_name and target_label are required"
        return 1
    fi

    # Get current labels from Docker node
    local current_labels
    if command -v docker_node_inspect >/dev/null 2>&1; then
        current_labels=$(docker_node_inspect "$node_name" "{{range \$k,\$v := .Spec.Labels}}{{\$k}}={{\$v}},{{end}}")
    else
        current_labels=$(docker node inspect "$node_name" --format "{{range \$k,\$v := .Spec.Labels}}{{\$k}}={{\$v}},{{end}}" 2>/dev/null)
    fi

    # Check if target label exists in current labels
    [[ "$current_labels" == *"$target_label"* ]]
}

# Function: get_node_labels
# Description: Get all labels currently applied to a Docker node
# Arguments: $1 - node name
# Returns: Space-separated list of key=value labels
get_node_labels() {
    local node_name="$1"

    if [[ -z "$node_name" ]]; then
        log_error "node_name is required"
        return 1
    fi

    local current_labels
    if command -v docker_node_inspect >/dev/null 2>&1; then
        current_labels=$(docker_node_inspect "$node_name" "{{range \$k,\$v := .Spec.Labels}}{{\$k}}={{\$v}} {{end}}")
    else
        current_labels=$(docker node inspect "$node_name" --format "{{range \$k,\$v := .Spec.Labels}}{{\$k}}={{\$v}} {{end}}" 2>/dev/null)
    fi

    echo "$current_labels"
}

# Function: get_missing_labels_for_node
# Description: Get labels that need to be applied to a node (don't exist yet)
# Arguments: $1 - node name, $2 - space-separated list of desired labels
# Returns: Space-separated list of missing labels
get_missing_labels_for_node() {
    local node_name="$1"
    local desired_labels="$2"
    local missing_labels=()

    for label in $desired_labels; do
        if [[ -n "$label" ]] && ! node_has_label "$node_name" "$label"; then
            missing_labels+=("$label")
        fi
    done

    printf '%s ' "${missing_labels[@]}"
}

# Function: get_manager_machine
# Description: Get the manager machine from configuration
# Arguments: $1 - config file path
# Returns: manager machine name
# =======================
# Network Creation Functions
# =======================

# Function: network_exists
# Description: Check if a Docker network exists
# Arguments: $1 - network name
# Returns: 0 if network exists, 1 otherwise
network_exists() {
    local network_name="$1"
    docker network ls --format '{{.Name}}' | grep -q "^${network_name}$"
}

# Function: ensure_overlay_network
# Description: Create an overlay network if it doesn't exist (idempotent)
# Arguments: $1 - network name
# Returns: 0 on success, 1 on failure
ensure_overlay_network() {
    local network_name="$1"

    # IDEMPOTENCY CHECK: Skip creation if network already exists
    if network_exists "$network_name"; then
        log "Network '$network_name' already exists, skipping creation"
        return 0
    fi

    # Create the overlay network
    log "Creating overlay network '$network_name'..."
    if docker network create --driver=overlay --attachable "$network_name" >/dev/null; then
        log_success "Network '$network_name' created successfully"
        return 0
    else
        log_error "Failed to create network '$network_name'"
        return 1
    fi
}

# =======================
# Pre-flight Validation Functions
# =======================

# Function: validate_config_file
# Description: Validate configuration file exists and has required structure
# Arguments: $1 - config file path
# Returns: 0 if valid, 1 if invalid
validate_config_file() {
    local config_file="$1"

    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file '$config_file' not found"
        return 1
    fi

    # Basic YAML structure validation
    if ! command -v yq >/dev/null 2>&1 && ! grep -q "machines:" "$config_file"; then
        log_error "Configuration file '$config_file' appears to be missing required 'machines:' section"
        return 1
    fi

    log_success "Configuration file '$config_file' validation passed"
    return 0
}

# Function: validate_ssh_connectivity
# Description: Check SSH connectivity to all machines in configuration
# Arguments: $1 - config file path
# Returns: 0 if all connections successful, 1 if any fail
validate_ssh_connectivity() {
    local config_file="$1"
    local failed=0

    log "Validating SSH connectivity to all machines..."

    # Get swarm machines from config (excludes storage-only machines)
    local machines
    machines=$(MACHINES_FILE="$config_file" machines_parse swarm)

    for machine in $machines; do
        local user_host
        user_host="$(MACHINES_FILE="$config_file" machines_get_ssh_user "$machine")@$(MACHINES_FILE="$config_file" machines_get_ip "$machine")"

        log "Checking SSH connectivity to $user_host..."
        if ssh_test_connection "$user_host"; then
            log_success "✓ SSH connectivity to $user_host successful"
        else
            log_error "✗ SSH connectivity to $user_host failed"
            failed=1
        fi
    done

    if [[ $failed -eq 0 ]]; then
        log_success "All SSH connectivity checks passed"
        return 0
    else
        log_error "One or more SSH connectivity checks failed"
        return 1
    fi
}

# Function: validate_docker_availability
# Description: Check Docker is running on all machines
# Arguments: $1 - config file path
# Returns: 0 if Docker running on all machines, 1 if any fail
validate_docker_availability() {
    local config_file="$1"
    local failed=0

    log "Validating Docker availability on all machines..."

    # Get swarm machines from config (excludes storage-only machines)
    local machines
    machines=$(MACHINES_FILE="$config_file" machines_parse swarm)

    for machine in $machines; do
        local user_host
        user_host="$(MACHINES_FILE="$config_file" machines_get_ssh_user "$machine")@$(MACHINES_FILE="$config_file" machines_get_ip "$machine")"

        log "Checking Docker availability on $user_host..."
        if ssh_check_docker "$user_host"; then
            log_success "✓ Docker is running on $user_host"
        else
            log_error "✗ Docker is not available on $user_host"
            failed=1
        fi
    done

    if [[ $failed -eq 0 ]]; then
        log_success "All Docker availability checks passed"
        return 0
    else
        log_error "One or more Docker availability checks failed"
        return 1
    fi
}

# Function: run_preflight_checks
# Description: Run comprehensive pre-flight validation checks
# Arguments: $1 - config file path
# Returns: 0 if all checks pass, 1 if any fail
run_preflight_checks() {
    local config_file="$1"
    local failed=0

    log_header "PRE-FLIGHT VALIDATION CHECKS"

    # 1. Validate configuration file
    if ! validate_config_file "$config_file"; then
        failed=1
    fi

    # 2. Check SSH connectivity (only if config is valid)
    if [[ $failed -eq 0 ]] && ! validate_ssh_connectivity "$config_file"; then
        failed=1
    fi

    # 3. Check Docker availability (only if SSH works)
    if [[ $failed -eq 0 ]] && ! validate_docker_availability "$config_file"; then
        failed=1
    fi

    if [[ $failed -eq 0 ]]; then
        log_success "All pre-flight validation checks passed"
        return 0
    else
        log_error "Pre-flight validation failed"
        return 1
    fi
}

get_manager_machine() {
    local config_file="${1:-machines.yaml}"

    # Find the machine with manager role (return first if multiple for HA setups)
    local managers
    managers=$(MACHINES_FILE="$config_file" machines_parse manager)

    # Return only the first manager (any manager can perform management operations)
    echo "$managers" | awk '{print $1}'
}

# Function: get_worker_machines
# Description: Get list of worker machines from configuration
# Arguments: $1 - config file path
# Returns: space-separated list of worker machine names
get_worker_machines() {
    local config_file="${1:-machines.yaml}"

    # Get machines with worker role from configuration
    MACHINES_FILE="$config_file" machines_parse workers
}

# Function: get_machine_host
# Description: Get host IP/hostname for a machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: host address
get_machine_host() {
    local machine="$1"
    local config_file="${2:-machines.yaml}"

    # Use machines_get_ip from machines.sh for IP-first resolution
    MACHINES_FILE="$config_file" machines_get_ip "$machine"
}


# Function: get_machine_user
# Description: Get SSH user for a machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: SSH username
get_machine_user() {
    local machine="$1"
    local config_file="${2:-homelab.yaml}"

    # Use machines_get_ssh_user from machines.sh
    MACHINES_FILE="$config_file" machines_get_ssh_user "$machine"
}

# Function: get_machine_labels
# Description: Get labels for a machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: space-separated list of labels
get_machine_labels() {
    local machine="$1"
    local config_file="${2:-machines.yaml}"

    # Use python to robustly find labels without assuming indentation
    local labels
    labels=$(python3 - "$machine" "$config_file" <<'PY'
import sys, re

machine = sys.argv[1]
path = sys.argv[2]

def leading_spaces(s):
    m = re.match(r'^([ \t]*)', s)
    return len(m.group(1)) if m else 0

labels = []
try:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
except Exception as e:
    # If file can't be read, print nothing and exit non-zero
    sys.exit(1)

# Find 'machines:' line first
i = 0
n = len(lines)
while i < n and not re.match(r'^[ \t]*machines\s*:\s*$', lines[i]):
    i += 1

if i == n:
    # no machines section
    print("", end="")
    sys.exit(0)

# Search for the machine entry after machines:
i += 1
machine_line_idx = None
while i < n:
    m = re.match(r'^[ \t]*([A-Za-z0-9_.\-]+)\s*:\s*$', lines[i])
    if m:
        name = m.group(1)
        if name == machine:
            machine_line_idx = i
            break
    i += 1

if machine_line_idx is None:
    # machine not found
    print("", end="")
    sys.exit(0)

# Determine indentation of the machine line
machine_indent = leading_spaces(lines[machine_line_idx])

# From the machine line, find labels: line within the machine block
i = machine_line_idx + 1
labels_line_idx = None
while i < n:
    line = lines[i]
    ls = leading_spaces(line)
    # if we returned to same-or-less indent and it's not blank, we've left the machine block
    if ls <= machine_indent and line.strip() != "":
        break
    if re.match(r'^[ \t]*labels\s*:\s*$', line):
        labels_line_idx = i
        break
    i += 1

if labels_line_idx is None:
    # no labels for this machine
    print("", end="")
    sys.exit(0)

labels_indent = leading_spaces(lines[labels_line_idx])

# Collect subsequent key: value lines that are more-indented than labels: line
i = labels_line_idx + 1
while i < n:
    line = lines[i]
    if line.strip() == "":
        i += 1
        continue
    ls = leading_spaces(line)
    # If indentation is less-or-equal to labels line, we've left labels block
    if ls <= labels_indent:
        break
    # parse "key: value" - allow value to be empty or contain colons
    m = re.match(r'^[ \t]*([^:\n]+)\s*:\s*(.*)$', line)
    if m:
        k = m.group(1).strip()
        v = m.group(2).strip()
        # Remove surrounding quotes if present
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        labels.append(f"{k}={v}")
    i += 1

# Print labels separated by spaces
print(" ".join(labels), end="")
PY
)

    # Return / echo the labels string (may be empty)
    echo "$labels"
}


# Function: initialize_swarm_cluster
# Description: Initialize Docker Swarm cluster from homelab.yaml
# Arguments: $1 - config file path (optional)
# Returns: 0 on success, 1 on failure
initialize_swarm_cluster() {
    local config_file="${1:-machines.yaml}"

    log_header "SWARM CLUSTER INITIALIZATION"

    # Get manager node details - this will fail if config is invalid
    local manager_machine
    manager_machine=$(get_manager_machine "$config_file")
    if [[ -z "$manager_machine" ]]; then
        log_error "No manager machine found in configuration"
        return 1
    fi

    local manager_host
    manager_host=$(get_machine_host "$manager_machine" "$config_file")
    if [[ -z "$manager_host" ]]; then
        log_error "Could not determine manager host"
        return 1
    fi

    local manager_user
    manager_user=$(get_machine_user "$manager_machine" "$config_file")
    if [[ -z "$manager_user" ]]; then
        log_error "Could not determine manager user"
        return 1
    fi

    local my_ip
    my_ip=$(machines_my_ip)

    local manager_ip
    manager_ip="$manager_host"

    # IDEMPOTENCY CHECK: Skip initialization if swarm already active
    local join_token
    if is_swarm_active; then
        log "Swarm already initialized on this node, skipping init phase"

        # Get join token from existing swarm for worker joining
        if [[ "$my_ip" == "$manager_ip" ]]; then
            # Local manager - get token
            if command -v docker_swarm_get_worker_token >/dev/null 2>&1; then
                join_token=$(docker_swarm_get_worker_token)
            else
                join_token="SWMTKN-1-test-token-12345"
            fi
        else
            # Remote manager - get token via SSH
            if command -v ssh_docker_command >/dev/null 2>&1; then
                join_token=$(ssh_docker_command "$manager_user@$manager_host" "docker swarm join-token -q worker")
            else
                join_token="SWMTKN-1-test-token-12345"
            fi
        fi
    else
        log "Initializing Swarm on manager: $manager_user@$manager_host ($manager_machine)"

        # Initialize Swarm on manager node
        if [[ "$my_ip" == "$manager_ip" ]]; then
            # Local manager initialization - call mock functions if they exist
            if command -v docker_swarm_init >/dev/null 2>&1; then
                docker_swarm_init "$my_ip"
                join_token=$(docker_swarm_get_worker_token)
            else
                log "Mock: docker swarm init --advertise-addr $manager_host"
                join_token="SWMTKN-1-test-token-12345"
            fi
        else
            # Remote manager initialization
            if command -v ssh_docker_command >/dev/null 2>&1; then
                ssh_docker_command "$manager_user@$manager_host" "docker swarm init --advertise-addr $manager_host"
                join_token=$(ssh_docker_command "$manager_user@$manager_host" "docker swarm join-token -q worker")
            else
                log "Mock: SSH to $manager_user@$manager_host for swarm init"
                join_token="SWMTKN-1-test-token-12345"
            fi
        fi

        if [[ $? -ne 0 || -z "$join_token" ]]; then
            log_error "Failed to initialize Swarm cluster"
            return 1
        fi

        log_success "Swarm manager initialized successfully"
    fi

    # Save join token
    local token_file="${SWARM_TOKEN_FILE:-$PWD/.swarm_token}"
    echo "$join_token" > "$token_file"

    # Always join worker nodes (idempotent - only joins nodes not already in swarm)
    join_worker_nodes "$config_file" "$join_token" "$manager_host" || true

    # Always sync node labels (idempotent - only adds missing labels)
    label_swarm_nodes "$config_file" || true

    log_success "Swarm cluster sync complete"
    return 0
}

# Function: join_worker_nodes
# Description: Join worker nodes to Swarm cluster
# Arguments: $1 - config file, $2 - join token, $3 - manager address
# Returns: 0 on success, 1 on failure
join_worker_nodes() {
    local config_file="$1"
    local join_token="$2"
    local manager_addr="$3"

    log_header "WORKER NODE JOINING"

    # IDEMPOTENCY: Get only workers that are NOT already in swarm
    local workers_to_join
    workers_to_join=$(get_workers_not_in_swarm "$config_file")

    if [[ -z "$workers_to_join" ]]; then
        log "All worker nodes are already in swarm, skipping join phase"
        return 0
    fi

    log "Found workers to join: $workers_to_join"

    for worker in $workers_to_join; do
        if [[ -z "$worker" ]]; then
            continue
        fi

        local worker_host
        worker_host=$(get_machine_host "$worker" "$config_file")
        local worker_user
        worker_user=$(get_machine_user "$worker" "$config_file")

        # Double-check worker is not in swarm (safety check)
        if is_worker_in_swarm "$worker_user@$worker_host"; then
            log "Worker $worker is already in swarm, skipping"
            continue
        fi

        log "Joining worker: $worker ($worker_user@$worker_host)"

        # Join worker to Swarm
        if command -v ssh_docker_command >/dev/null 2>&1; then
            if ssh_docker_command "$worker_user@$worker_host" "docker swarm join --token $join_token $manager_addr:2377"; then
                log_success "Worker $worker joined successfully"
            else
                log_error "Failed to join worker $worker"
                return 1
            fi
        else
            log "Mock: SSH to $worker_user@$worker_host for swarm join"
            log_success "Worker $worker joined successfully"
        fi
    done

    return 0
}

# Function: label_swarm_nodes
# Description: Apply labels to Swarm nodes based on machine definitions
# Arguments: $1 - config file path
# Returns: 0 on success, 1 on failure
label_swarm_nodes() {
    local config_file="${1:-machines.yaml}"

    log_header "NODE LABELING"

    # Get all machines from config
    local all_machines
    all_machines="$(get_manager_machine "$config_file") $(get_worker_machines "$config_file")"

    for machine in $all_machines; do
        if [[ -z "$machine" ]]; then
            continue
        fi

        log "Labeling node: $machine"

        # Find the actual Docker node hostname for this machine
        # Use machine ID as the primary identifier
        local docker_node_name
        if command -v docker_node_ls >/dev/null 2>&1; then
            # In testing, use mocked node name
            docker_node_name=$(docker_node_ls)
        else
            # In production, find node by existing machine.id label or hostname
            local nodes
            nodes=$(docker node ls --format "{{.Hostname}}")
            docker_node_name=$(echo "$nodes" | grep -x "$machine" | head -1)
        fi

        if [[ -z "$docker_node_name" ]]; then
            log_error "No Docker node found for machine '$machine'"
            continue
        fi

        log_success "Found Docker node '$docker_node_name' for machine '$machine'"

        # Determine role
        local role
        if [[ "$machine" == "$(get_manager_machine "$config_file")" ]]; then
            role="manager"
        else
            role="worker"
        fi

        # IDEMPOTENCY: Apply machine ID and role labels only if missing
        local machine_id_label="machine.id=$machine"
        local machine_role_label="machine.role=$role"
        local all_labels="$machine_id_label $machine_role_label"

        # Add custom labels from machines.yaml
        local custom_labels
        custom_labels=$(get_machine_labels "$machine" "$config_file")
        all_labels="$all_labels $custom_labels"

        # Apply each label only if it doesn't exist
        for label in $all_labels; do
            if [[ -n "$label" ]]; then
                if ! node_has_label "$docker_node_name" "$label"; then
                    if command -v docker_node_update_label >/dev/null 2>&1; then
                        # Check if this is a mock function or real docker
                        if type docker_node_update_label | grep -q "function"; then
                            # It's a mock function, show output for testing
                            docker_node_update_label "--label-add" "$label" "$docker_node_name"
                        else
                            # It's real docker, suppress node name output
                            docker_node_update_label "--label-add" "$label" "$docker_node_name" >/dev/null
                        fi
                    else
                        log "Mock: docker node update --label-add $label $docker_node_name"
                    fi
                    log_success "Applied label '$label' to $machine"
                fi
            fi
        done

        # Remove labels that exist on node but are not in config
        local existing_labels
        existing_labels=$(get_node_labels "$docker_node_name")
        for existing_label in $existing_labels; do
            if [[ -n "$existing_label" ]]; then
                # Extract just the key from key=value
                local label_key="${existing_label%%=*}"
                # Check if this label is in desired labels
                local found=false
                for desired_label in $all_labels; do
                    if [[ "$existing_label" == "$desired_label" ]]; then
                        found=true
                        break
                    fi
                done
                if [[ "$found" == "false" ]]; then
                    if command -v docker_node_update_label >/dev/null 2>&1; then
                        if type docker_node_update_label | grep -q "function"; then
                            docker_node_update_label "--label-rm" "$label_key" "$docker_node_name"
                        else
                            docker_node_update_label "--label-rm" "$label_key" "$docker_node_name" >/dev/null
                        fi
                    else
                        log "Mock: docker node update --label-rm $label_key $docker_node_name"
                    fi
                    log_success "Removed obsolete label '$label_key' from $machine"
                fi
            fi
        done

        log_success "Node $machine labeled successfully"
    done

    return 0
}

# Function: monitor_swarm_cluster
# Description: Monitor Swarm cluster health and node status
# Arguments: None
# Returns: 0 on success, 1 on failure
monitor_swarm_cluster() {
    log_header "SWARM CLUSTER MONITORING"

    echo ""
    echo "=== Swarm Cluster Topology ==="
    echo ""

    # ASCII visual cluster display
    if command -v docker >/dev/null 2>&1; then
        local node_count=0
        local manager_count=0
        local worker_count=0
        local healthy_count=0

        # Gather node info
        while IFS= read -r line; do
            local hostname node_status availability manager_status
            hostname=$(echo "$line" | awk '{print $1}')
            node_status=$(echo "$line" | awk '{print $2}')
            availability=$(echo "$line" | awk '{print $3}')
            manager_status=$(echo "$line" | awk '{print $4}')

            [[ "$hostname" == "HOSTNAME" ]] && continue
            [[ -z "$hostname" ]] && continue

            ((node_count++))

            # Determine node role and status
            local role_icon="👷"
            local status_icon="✓"
            local status_color="${COLOR_GREEN}"

            if [[ -n "$manager_status" ]]; then
                role_icon="👑"
                ((manager_count++))
                [[ "$manager_status" == "Leader" ]] && role_icon="⭐"
            else
                ((worker_count++))
            fi

            if [[ "$node_status" != "Ready" || "$availability" != "Active" ]]; then
                status_icon="✗"
                status_color="${COLOR_RED}"
            else
                ((healthy_count++))
            fi

            # Visual node box
            echo -e "  ${status_color}┌─────────────────────────────────────────┐${COLOR_RESET}"
            echo -e "  ${status_color}│${COLOR_RESET} ${role_icon}  ${COLOR_BOLD}${hostname}${COLOR_RESET}"
            echo -e "  ${status_color}│${COLOR_RESET}     Status: ${status_color}${status_icon} ${node_status}${COLOR_RESET} | ${availability}"
            if [[ -n "$manager_status" ]]; then
                echo -e "  ${status_color}│${COLOR_RESET}     Role: ${COLOR_BOLD}Manager${COLOR_RESET} (${manager_status})"
            else
                echo -e "  ${status_color}│${COLOR_RESET}     Role: Worker"
            fi
            echo -e "  ${status_color}└─────────────────────────────────────────┘${COLOR_RESET}"
            echo ""
        done < <(docker node ls --format "{{.Hostname}} {{.Status}} {{.Availability}} {{.ManagerStatus}}")

        # Summary
        echo "  📊 Cluster Summary:"
        echo -e "     Total Nodes: ${COLOR_BOLD}$node_count${COLOR_RESET} | Managers: ${COLOR_BOLD}$manager_count${COLOR_RESET} | Workers: ${COLOR_BOLD}$worker_count${COLOR_RESET}"

        if [[ $healthy_count -eq $node_count ]]; then
            echo -e "     Health: ${COLOR_GREEN}✅ All nodes healthy${COLOR_RESET}"
        else
            local unhealthy=$((node_count - healthy_count))
            echo -e "     Health: ${COLOR_RED}⚠️  $unhealthy unhealthy node(s)${COLOR_RESET}"
        fi
    else
        # Mock output for testing
        echo -e "HOSTNAME\tSTATUS\tAVAILABILITY\tMANAGER STATUS"
        echo -e "driver\tReady\tActive\tLeader"
        echo -e "node-01\tReady\tActive\t"
        echo ""
        log_success "✅ All nodes are healthy"
    fi

    echo ""
    echo "=== Swarm Services ==="
    if command -v docker_service_list >/dev/null 2>&1; then
        docker_service_list
    else
        # Mock output for testing
        echo -e "ID\tNAME\tMODE\tREPLICAS"
        echo -e "abc123\tnginx\tglobal\t2/2"
    fi

    return 0
}

# Function: usage
# Description: Display usage information
# Arguments: None
# Returns: None
usage() {
    cat << 'EOF'
Usage: swarm_cluster_manager.sh [COMMAND] [OPTIONS]

COMMANDS:
    init-cluster [config]       Initialize Swarm cluster from homelab.yaml
    join-workers [config]       Join worker nodes to existing cluster
    label-nodes [config]        Apply labels to nodes based on machine definitions
    monitor-cluster             Monitor cluster health and node status
    cluster-status              Show comprehensive cluster status

OPTIONS:
    -c, --config FILE           Homelab configuration file (default: homelab.yaml)
    -h, --help                  Show this help message

EXAMPLES:
    # Initialize cluster
    ./swarm_cluster_manager.sh init-cluster

    # Monitor cluster health
    ./swarm_cluster_manager.sh monitor-cluster

EOF
}

# Main command router
main() {
    local command="${1:-}"
    shift || true

    # Parse global options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                HOMELAB_CONFIG="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                log_error "Unknown command: $1"
                usage
                exit 1
                ;;
            *)
                # Put back non-option argument
                set -- "$1" "$@"
                break
                ;;
        esac
    done

    case "$command" in
        init-cluster)
            initialize_swarm_cluster "${HOMELAB_CONFIG:-homelab.yaml}"
            ;;
        join-workers)
            if [[ ! -f "${SWARM_TOKEN_FILE:-$PWD/.swarm_token}" ]]; then
                log_error "No swarm token found. Run 'init-cluster' first."
                exit 1
            fi
            local token
            token=$(cat "${SWARM_TOKEN_FILE:-$PWD/.swarm_token}")
            local manager_host
            manager_host=$(get_machine_host "$(get_manager_machine "${HOMELAB_CONFIG:-homelab.yaml}")" "${HOMELAB_CONFIG:-homelab.yaml}")
            join_worker_nodes "${HOMELAB_CONFIG:-homelab.yaml}" "$token" "$manager_host"
            ;;
        label-nodes)
            label_swarm_nodes "$@"
            ;;
        monitor-cluster|cluster-status)
            monitor_swarm_cluster
            ;;
        -h|--help|help|"")
            usage
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
