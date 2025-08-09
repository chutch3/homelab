#!/bin/bash

# Source wrapper interfaces for external dependencies
source scripts/wrappers/docker_wrapper.sh
source scripts/wrappers/file_wrapper.sh
source scripts/ssh.sh


swarm_setup_certificates() {
    load_env

    echo "Creating swarm secrets for $BASE_DOMAIN"

    # Create Docker secrets from your existing cert files
    docker_secret_create "ssl_full.pem" "${PROJECT_ROOT}/certs/${BASE_DOMAIN}_ecc/fullchain.cer"
    docker_secret_create "ssl_key.pem" "${PROJECT_ROOT}/certs/${BASE_DOMAIN}_ecc/${BASE_DOMAIN}.key"
    docker_secret_create "ssl_ca.pem" "${PROJECT_ROOT}/certs/${BASE_DOMAIN}_ecc/ca.cer"
    docker_secret_create "ssl_dhparam.pem" "${PROJECT_ROOT}/certs/dhparam.pem"
}



swarm_initialize_manager() {
    echo "Initializing swarm on manager node..."

    # Get manager hostname
    MANAGER_HOST=$(machines_parse manager)
    MANAGER_IP=$(machines_get_host_ip "$MANAGER_HOST")

    echo "Resolved manager IP: $MANAGER_IP"

    # Initialize swarm
    docker_swarm_init "$MANAGER_IP"
    docker_swarm_get_worker_token > .swarm_token
}


# Initial setup of swarm cluster
swarm_setup_cluster() {
    # First ensure we have a token
    # if [ ! -f .swarm_token ]; then
    #     echo "No swarm token found. Running swarm init first..."
    #     swarm_initialize_manager
    # fi
    swarm_initialize_manager

    # Initialize certificates
    ensure_certs_exist

    # Create Docker secrets
    swarm_setup_certificates

    # Sync nodes to match configuration
    swarm_sync_nodes
}

# Join a node to the swarm
swarm_add_worker_node() {
    local host=$1
    local token
    local manager_host
    local manager_ip
    local ssh_user

    token=$(file_read .swarm_token)
    manager_host=$(machines_parse manager)
    manager_ip=$(machines_get_host_ip "$manager_host")
    ssh_user=$(machines_get_ssh_user "$host")

    if [ "$ssh_user" = "null" ]; then
        ssh_user=${USER}
    fi

    echo "Joining node $host to swarm..."
    ssh_docker_command "$ssh_user@$host" "docker swarm join --token $token ${manager_ip}:2377"
}

# Ongoing maintenance of swarm nodes
swarm_sync_nodes() {
    echo "Syncing swarm nodes with machines.yml configuration..."

    # Get current worker nodes from swarm
    current_nodes=$(docker_node_list '{{.Hostname}}' | grep -v "$(machines_parse manager)")
    echo "Current nodes: $current_nodes"

    # Get desired worker nodes from machines.yml
    desired_nodes=$(machines_parse workers)
    echo "Desired nodes: $desired_nodes"

    # Remove nodes that shouldn't be there
    for node in $current_nodes; do
        if ! echo "$desired_nodes" | grep -q "$node"; then
            echo "Removing node $node from swarm..."
            docker_node_update_availability "drain" "$node"
            sleep 5  # Wait for services to drain
            docker_node_remove "$node" "--force"
            local ssh_user
            ssh_user=$(machines_get_ssh_user "$node")
            if [ "$ssh_user" = "null" ]; then
                ssh_user=${USER}
            fi
            ssh_docker_command "$ssh_user@$node" "docker swarm leave --force"
        fi
    done

    # Add new nodes
    for node in $desired_nodes; do
        if ! docker_node_list '{{.Hostname}}' | grep -q "$node"; then
            echo "Adding new node $node to swarm..."
            swarm_add_worker_node "$node"
        fi
    done

    # Update labels
    for node in $desired_nodes; do
        echo "Updating labels for node $node..."
        # Remove existing labels
        current_labels=$(docker_node_inspect "$node" "{{range \$k,\$v := .Spec.Labels}}{{\$k}}{{end}}")
        for label in $current_labels; do
            docker_node_update_label "--label-rm" "$label" "$node"
        done

        # Add new labels
        labels=$(machines_parse ".workers[] | select(.host == \"$node\") | .labels")
        if [ -n "$labels" ]; then
            for label in $labels; do
                docker_node_update_label "--label-add" "$label" "$node"
            done
        fi
    done

    echo "Swarm node sync complete."
    swarm_display_status
}

swarm_display_status() {
    echo "Swarm Nodes:"
    docker_node_list

    echo -e "\nSwarm Services:"
    docker_service_list
}
