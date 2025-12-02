#!/bin/bash

# Docker wrapper interface to enable testing by abstracting docker commands
# This follows the principle of not mocking third-party dependencies
# Instead, we create a thin wrapper that can be easily substituted in tests

# Initialize docker swarm
# Args:
#   $1: advertise address
# Returns:
#   docker command exit code
docker_swarm_init() {
    local advertise_addr="$1"
    docker swarm init --advertise-addr "$advertise_addr"
}

# Get docker swarm join token for workers
# Returns:
#   worker join token to stdout
docker_swarm_get_worker_token() {
    docker swarm join-token -q worker
}

# Create docker secret
# Args:
#   $1: secret name
#   $2: secret file path
# Returns:
#   docker command exit code
docker_secret_create() {
    local secret_name="$1"
    local secret_file="$2"
    docker secret create "$secret_name" "$secret_file"
}

# List docker nodes with custom format
# Args:
#   $1: format string
# Returns:
#   formatted node list to stdout
docker_node_list() {
    local format="${1:-{{.Hostname}}}"
    docker node ls --format "$format"
}

# Update docker node availability
# Args:
#   $1: availability (drain, active, pause)
#   $2: node name
# Returns:
#   docker command exit code
docker_node_update_availability() {
    local availability="$1"
    local node="$2"
    docker node update --availability "$availability" "$node"
}

# Remove docker node
# Args:
#   $1: node name
#   $2: additional flags (optional, e.g., --force)
# Returns:
#   docker command exit code
docker_node_remove() {
    local node="$1"
    local flags="${2:-}"
    docker node rm "$flags" "$node"
}

# Inspect docker node
# Args:
#   $1: node name
#   $2: format string
# Returns:
#   formatted node info to stdout
docker_node_inspect() {
    local node="$1"
    local format="$2"
    docker node inspect "$node" --format "$format"
}

# Update docker node labels
# Args:
#   $1: action (--label-add or --label-rm)
#   $2: label
#   $3: node name
# Returns:
#   docker command exit code
docker_node_update_label() {
    local action="$1"
    local label="$2"
    local node="$3"

    # Check if we're in test mode with a mock function available
    if command -v mock_docker_node_update_label >/dev/null 2>&1; then
        mock_docker_node_update_label "$action" "$label" "$node"
    else
        docker node update "$action" "$label" "$node"
    fi
}

# List docker services
# Returns:
#   service list to stdout
docker_service_list() {
    docker service ls
}

# Join docker swarm as worker
# Args:
#   $1: join token
#   $2: manager address (e.g., 192.168.1.10:2377)
# Returns:
#   docker command exit code
docker_swarm_join() {
    local token="$1"
    local manager_addr="$2"
    docker swarm join --token "$token" "$manager_addr"
}

# Leave docker swarm
# Args:
#   $1: additional flags (optional, e.g., --force)
# Returns:
#   docker command exit code
docker_swarm_leave() {
    local flags="${1:-}"
    docker swarm leave "$flags"
}

# Export all functions for use in other scripts
export -f docker_swarm_init
export -f docker_swarm_get_worker_token
export -f docker_secret_create
export -f docker_node_list
export -f docker_node_update_availability
export -f docker_node_remove
export -f docker_node_inspect
export -f docker_node_update_label
export -f docker_service_list
export -f docker_swarm_join
export -f docker_swarm_leave
