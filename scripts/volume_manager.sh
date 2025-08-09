#!/bin/bash

# Volume Manager
# Provides centralized volume management for local and NFS storage

# Set default paths
PROJECT_ROOT="${PROJECT_ROOT:-$PWD}"
SERVICES_CONFIG="${SERVICES_CONFIG:-$PROJECT_ROOT/config/services.yaml}"
VOLUMES_CONFIG="${VOLUMES_CONFIG:-$PROJECT_ROOT/config/volumes.yaml}"
VOLUMES_ENV_FILE="${VOLUMES_ENV_FILE:-$PROJECT_ROOT/.volumes}"

# Load common functions if available
if [ -f "$PROJECT_ROOT/scripts/common.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/common.sh"
fi

# Function: load_volume_config
# Description: Loads volume configuration from volumes.yaml
# Arguments: None
# Returns: Sets environment variables for volume configuration
load_volume_config() {
    if [ ! -f "$VOLUMES_CONFIG" ]; then
        echo "⚠️  Warning: Volume configuration not found at $VOLUMES_CONFIG"
        echo "💡 Using default local storage configuration"

        # Set default local storage
        export VOLUME_STORAGE_TYPE="local"
        export VOLUME_BASE_PATH="${PROJECT_ROOT}/appdata"
        export VOLUME_OWNER="${UID:-1000}"
        export VOLUME_GROUP="${GID:-1000}"
        export VOLUME_PERMISSIONS="755"
        return 0
    fi

    # Load storage type configuration
    local storage_type
    if yq '.storage.nfs.enabled' "$VOLUMES_CONFIG" | grep -q true; then
        storage_type="nfs"
        export VOLUME_STORAGE_TYPE="nfs"
        export NFS_SERVER=$(yq -r '.storage.nfs.server' "$VOLUMES_CONFIG")
        export NFS_EXPORT_PATH=$(yq -r '.storage.nfs.export_path' "$VOLUMES_CONFIG")
        export NFS_MOUNT_POINT=$(yq -r '.storage.nfs.mount_point' "$VOLUMES_CONFIG")
        export NFS_MOUNT_OPTIONS=$(yq -r '.storage.nfs.mount_options' "$VOLUMES_CONFIG")
        export VOLUME_BASE_PATH="$NFS_MOUNT_POINT"
        export VOLUME_OWNER=$(yq -r '.storage.nfs.permissions.owner' "$VOLUMES_CONFIG")
        export VOLUME_GROUP=$(yq -r '.storage.nfs.permissions.group' "$VOLUMES_CONFIG")
        export VOLUME_PERMISSIONS=$(yq -r '.storage.nfs.permissions.mode' "$VOLUMES_CONFIG")
    else
        storage_type="local"
        export VOLUME_STORAGE_TYPE="local"
        export VOLUME_BASE_PATH=$(yq -r '.storage.local.base_path' "$VOLUMES_CONFIG")
        export VOLUME_OWNER=$(yq -r '.storage.local.permissions.owner' "$VOLUMES_CONFIG")
        export VOLUME_GROUP=$(yq -r '.storage.local.permissions.group' "$VOLUMES_CONFIG")
        export VOLUME_PERMISSIONS=$(yq -r '.storage.local.permissions.mode' "$VOLUMES_CONFIG")
    fi

    echo "📁 Loaded $storage_type storage configuration"
    echo "   Base path: $VOLUME_BASE_PATH"
    echo "   Owner: $VOLUME_OWNER:$VOLUME_GROUP"
    echo "   Permissions: $VOLUME_PERMISSIONS"
}

# Function: generate_volume_paths
# Description: Generates volume path environment variables from services.yaml
# Arguments: None
# Returns: Outputs volume environment variables
generate_volume_paths() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    load_volume_config

    echo "📂 Generating volume paths for $VOLUME_STORAGE_TYPE storage..."

    # Start the volumes environment file
    cat > "$VOLUMES_ENV_FILE" <<EOF
# Generated volume paths from config/services.yaml
# DO NOT EDIT - This file is auto-generated
# Generated $(date)

# Storage configuration
VOLUME_STORAGE_TYPE=$VOLUME_STORAGE_TYPE
VOLUME_BASE_PATH=$VOLUME_BASE_PATH
VOLUME_OWNER=$VOLUME_OWNER
VOLUME_GROUP=$VOLUME_GROUP
VOLUME_PERMISSIONS=$VOLUME_PERMISSIONS

EOF

    # Add NFS configuration if applicable
    if [ "$VOLUME_STORAGE_TYPE" = "nfs" ]; then
        cat >> "$VOLUMES_ENV_FILE" <<EOF
# NFS configuration
NFS_SERVER=$NFS_SERVER
NFS_EXPORT_PATH=$NFS_EXPORT_PATH
NFS_MOUNT_POINT=$NFS_MOUNT_POINT
NFS_MOUNT_OPTIONS=$NFS_MOUNT_OPTIONS

EOF
    fi

    echo "# Volume paths" >> "$VOLUMES_ENV_FILE"

    # Extract services and generate volume paths
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        # Check if service has volumes defined
        if yq ".services[\"${service_key}\"].volumes" "$SERVICES_CONFIG" | grep -q -v null; then
            echo "  Processing volumes for: $service_key"

            # Get number of volumes for this service
            volume_count=$(yq ".services[\"${service_key}\"].volumes | length" "$SERVICES_CONFIG")

            # Process each volume by index
            for i in $(seq 0 $((volume_count - 1))); do
                volume_name=$(yq ".services[\"${service_key}\"].volumes[$i].name" "$SERVICES_CONFIG" | tr -d '"')
                if [ "$volume_name" != "null" ] && [ -n "$volume_name" ]; then
                    # Generate volume path variable
                    service_var=$(echo "$service_key" | tr '[:lower:]' '[:upper:]' | sed 's/[^A-Z0-9]/_/g')
                    volume_var=$(echo "$volume_name" | tr '[:lower:]' '[:upper:]' | sed 's/[^A-Z0-9]/_/g')
                    volume_path="$VOLUME_BASE_PATH/${service_key}/${volume_name}"

                    echo "VOLUME_${service_var}_${volume_var}=${volume_path}" >> "$VOLUMES_ENV_FILE"
                    echo "VOLUME_${service_var}_${volume_var}=${volume_path}"
                fi
            done
        fi
    done

    echo "✅ Generated volume paths at $VOLUMES_ENV_FILE"
    return 0
}

# Function: validate_volume_config
# Description: Validates volume configuration and storage accessibility
# Arguments: None
# Returns: 0 if valid, 1 if invalid
validate_volume_config() {
    load_volume_config

    echo "🔍 Validating volume configuration..."

    # Check base path accessibility
    if [ "$VOLUME_STORAGE_TYPE" = "local" ]; then
        if [ ! -d "$VOLUME_BASE_PATH" ]; then
            echo "⚠️  Warning: Volume base path does not exist: $VOLUME_BASE_PATH"
            echo "💡 Run 'create_volume_directories' to create the directory structure"
        else
            if [ ! -w "$VOLUME_BASE_PATH" ]; then
                echo "❌ Error: Volume base path is not writable: $VOLUME_BASE_PATH"
                return 1
            fi
        fi
    elif [ "$VOLUME_STORAGE_TYPE" = "nfs" ]; then
        if ! command -v mount.nfs >/dev/null 2>&1; then
            echo "❌ Error: NFS client tools not installed"
            echo "💡 Install with: sudo apt-get install nfs-common"
            return 1
        fi

        if [ ! -d "$NFS_MOUNT_POINT" ]; then
            echo "⚠️  Warning: NFS mount point does not exist: $NFS_MOUNT_POINT"
            echo "💡 Will be created during NFS setup"
        fi

        # Test NFS server connectivity
        if ! timeout 5 nc -z "$NFS_SERVER" 2049 2>/dev/null; then
            echo "⚠️  Warning: Cannot connect to NFS server $NFS_SERVER on port 2049"
            echo "💡 Ensure NFS server is running and accessible"
        fi
    fi

    echo "✅ Volume configuration is valid"
    return 0
}

# Function: setup_nfs_mount
# Description: Sets up NFS mount for volume storage
# Arguments: --dry-run (optional)
# Returns: 0 on success, 1 on failure
setup_nfs_mount() {
    local dry_run=false
    if [ "$1" = "--dry-run" ]; then
        dry_run=true
    fi

    load_volume_config

    if [ "$VOLUME_STORAGE_TYPE" != "nfs" ]; then
        echo "ℹ️  NFS not configured, skipping NFS mount setup"
        return 0
    fi

    echo "🌐 Setting up NFS mount..."

    if $dry_run; then
        echo "Would create mount point: $NFS_MOUNT_POINT"
        echo "Would mount: $NFS_SERVER:$NFS_EXPORT_PATH -> $NFS_MOUNT_POINT"
        echo "Mount options: $NFS_MOUNT_OPTIONS"
        return 0
    fi

    # Create mount point
    if [ ! -d "$NFS_MOUNT_POINT" ]; then
        echo "Creating NFS mount point: $NFS_MOUNT_POINT"
        sudo mkdir -p "$NFS_MOUNT_POINT"
    fi

    # Check if already mounted
    if mount | grep -q "$NFS_MOUNT_POINT"; then
        echo "✅ NFS already mounted at $NFS_MOUNT_POINT"
        return 0
    fi

    # Mount NFS
    echo "Mounting NFS: $NFS_SERVER:$NFS_EXPORT_PATH -> $NFS_MOUNT_POINT"
    if sudo mount -t nfs -o "$NFS_MOUNT_OPTIONS" "$NFS_SERVER:$NFS_EXPORT_PATH" "$NFS_MOUNT_POINT"; then
        echo "✅ NFS mounted successfully"

        # Add to fstab for persistence
        local fstab_entry="$NFS_SERVER:$NFS_EXPORT_PATH $NFS_MOUNT_POINT nfs $NFS_MOUNT_OPTIONS 0 0"
        if ! grep -q "$NFS_MOUNT_POINT" /etc/fstab; then
            echo "Adding to /etc/fstab for persistence..."
            echo "$fstab_entry" | sudo tee -a /etc/fstab
        fi
        return 0
    else
        echo "❌ Failed to mount NFS"
        return 1
    fi
}

# Function: create_volume_directories
# Description: Creates directory structure for all service volumes
# Arguments: None
# Returns: 0 on success, 1 on failure
create_volume_directories() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    load_volume_config

    echo "📁 Creating volume directory structure..."

    # Ensure base directory exists
    if [ ! -d "$VOLUME_BASE_PATH" ]; then
        echo "Creating base volume directory: $VOLUME_BASE_PATH"
        mkdir -p "$VOLUME_BASE_PATH"
    fi

    # Extract services and create volume directories
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        # Check if service has volumes defined
        if yq ".services[\"${service_key}\"].volumes" "$SERVICES_CONFIG" | grep -q -v null; then
            echo "  Creating directories for: $service_key"

            # Get number of volumes for this service
            volume_count=$(yq ".services[\"${service_key}\"].volumes | length" "$SERVICES_CONFIG")

            # Process each volume by index
            for i in $(seq 0 $((volume_count - 1))); do
                volume_name=$(yq ".services[\"${service_key}\"].volumes[$i].name" "$SERVICES_CONFIG" | tr -d '"')
                if [ "$volume_name" != "null" ] && [ -n "$volume_name" ]; then
                    volume_path="$VOLUME_BASE_PATH/${service_key}/${volume_name}"

                    if [ ! -d "$volume_path" ]; then
                        echo "    Creating: $volume_path"
                        mkdir -p "$volume_path"

                        # Set ownership and permissions
                        if command -v chown >/dev/null 2>&1; then
                            chown "$VOLUME_OWNER:$VOLUME_GROUP" "$volume_path" 2>/dev/null || true
                        fi
                        chmod "$VOLUME_PERMISSIONS" "$volume_path" 2>/dev/null || true
                    fi
                fi
            done
        fi
    done

    echo "✅ Volume directories created"
    return 0
}

# Function: generate_backup_config
# Description: Generates backup configuration based on volume priorities
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_backup_config() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    load_volume_config

    echo "💾 Generating backup configuration..."

    local backup_script="$PROJECT_ROOT/backup-config.sh"

    cat > "$backup_script" <<EOF
#!/bin/bash
# Generated backup configuration
# DO NOT EDIT - This file is auto-generated
# Generated $(date)

# Storage configuration
VOLUME_BASE_PATH="$VOLUME_BASE_PATH"
BACKUP_BASE_PATH="\${BACKUP_BASE_PATH:-$VOLUME_BASE_PATH/../backups}"

# High priority volumes (daily backup)
HIGH_PRIORITY_VOLUMES=(
EOF

    # Extract high priority volumes
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        if yq ".services[\"${service_key}\"].volumes" "$SERVICES_CONFIG" | grep -q -v null; then
            volume_count=$(yq ".services[\"${service_key}\"].volumes | length" "$SERVICES_CONFIG")

            for i in $(seq 0 $((volume_count - 1))); do
                volume_name=$(yq ".services[\"${service_key}\"].volumes[$i].name" "$SERVICES_CONFIG" | tr -d '"')
                backup_priority=$(yq ".services[\"${service_key}\"].volumes[$i].backup_priority" "$SERVICES_CONFIG" | tr -d '"')

                if [ "$backup_priority" = "high" ]; then
                    echo "    \"${service_key}/${volume_name}\"" >> "$backup_script"
                fi
            done
        fi
    done

    cat >> "$backup_script" <<EOF
)

# Medium priority volumes (weekly backup)
MEDIUM_PRIORITY_VOLUMES=(
EOF

    # Extract medium priority volumes
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        if yq ".services[\"${service_key}\"].volumes" "$SERVICES_CONFIG" | grep -q -v null; then
            volume_count=$(yq ".services[\"${service_key}\"].volumes | length" "$SERVICES_CONFIG")

            for i in $(seq 0 $((volume_count - 1))); do
                volume_name=$(yq ".services[\"${service_key}\"].volumes[$i].name" "$SERVICES_CONFIG" | tr -d '"')
                backup_priority=$(yq ".services[\"${service_key}\"].volumes[$i].backup_priority" "$SERVICES_CONFIG" | tr -d '"')

                if [ "$backup_priority" = "medium" ]; then
                    echo "    \"${service_key}/${volume_name}\"" >> "$backup_script"
                fi
            done
        fi
    done

    cat >> "$backup_script" <<EOF
)

# Backup functions
backup_high_priority() {
    echo "🔥 Backing up high priority volumes..."
    for volume in "\${HIGH_PRIORITY_VOLUMES[@]}"; do
        backup_volume "\$volume" "high"
    done
}

backup_medium_priority() {
    echo "📦 Backing up medium priority volumes..."
    for volume in "\${MEDIUM_PRIORITY_VOLUMES[@]}"; do
        backup_volume "\$volume" "medium"
    done
}

backup_volume() {
    local volume_path="\$1"
    local priority="\$2"
    local source_path="\$VOLUME_BASE_PATH/\$volume_path"
    local backup_path="\$BACKUP_BASE_PATH/\$volume_path"
    local timestamp=\$(date +%Y%m%d_%H%M%S)

    if [ -d "\$source_path" ]; then
        echo "  Backing up: \$volume_path (\$priority priority)"
        mkdir -p "\$(dirname "\$backup_path")"
        rsync -av "\$source_path/" "\$backup_path/\$timestamp/"

        # Create latest symlink
        ln -sfn "\$timestamp" "\$backup_path/latest"
    fi
}

# Execute backup based on argument
case "\$1" in
    high) backup_high_priority ;;
    medium) backup_medium_priority ;;
    all) backup_high_priority && backup_medium_priority ;;
    *) echo "Usage: \$0 {high|medium|all}" ;;
esac
EOF

    chmod +x "$backup_script"
    echo "✅ Generated backup configuration at $backup_script"
    return 0
}

# Function: show_volume_usage
# Description: Displays volume usage information
# Arguments: None
# Returns: 0 on success
show_volume_usage() {
    load_volume_config

    echo "📊 Volume Usage Report"
    echo "====================="
    echo "Storage Type: $VOLUME_STORAGE_TYPE"
    echo "Base Path: $VOLUME_BASE_PATH"
    echo ""

    if [ ! -d "$VOLUME_BASE_PATH" ]; then
        echo "⚠️  Volume base path does not exist: $VOLUME_BASE_PATH"
        return 1
    fi

    # Show overall disk usage
    echo "📈 Overall Storage Usage:"
    df -h "$VOLUME_BASE_PATH" 2>/dev/null || echo "Unable to get disk usage"
    echo ""

    echo "📁 Service Volume Usage:"
    # Show usage for each service directory
    find "$VOLUME_BASE_PATH" -maxdepth 2 -type d | while read -r dir; do
        if [ "$dir" != "$VOLUME_BASE_PATH" ]; then
            size=$(du -sh "$dir" 2>/dev/null | cut -f1)
            relative_path=$(echo "$dir" | sed "s|$VOLUME_BASE_PATH/||")
            echo "  $relative_path: $size"
        fi
    done

    return 0
}

# Function: migrate_volumes
# Description: Migrates volumes between storage locations
# Arguments: $1 - source path, $2 - destination path, $3 - --dry-run (optional)
# Returns: 0 on success, 1 on failure
migrate_volumes() {
    local source_path="$1"
    local dest_path="$2"
    local dry_run=false

    if [ "$3" = "--dry-run" ]; then
        dry_run=true
    fi

    if [ -z "$source_path" ] || [ -z "$dest_path" ]; then
        echo "❌ Error: Source and destination paths required"
        echo "Usage: migrate_volumes <source> <destination> [--dry-run]"
        return 1
    fi

    echo "🚛 Volume Migration"
    echo "==================="
    echo "Source: $source_path"
    echo "Destination: $dest_path"
    echo ""

    if [ ! -d "$source_path" ]; then
        echo "❌ Error: Source path does not exist: $source_path"
        return 1
    fi

    if $dry_run; then
        echo "🔍 Dry run mode - showing what would be migrated:"
        find "$source_path" -mindepth 1 -maxdepth 2 -type d | while read -r dir; do
            relative_path=$(echo "$dir" | sed "s|$source_path/||")
            echo "Would migrate: $relative_path"
        done
        return 0
    fi

    # Create destination directory
    mkdir -p "$dest_path"

    # Migrate each service directory
    find "$source_path" -mindepth 1 -maxdepth 1 -type d | while read -r service_dir; do
        service_name=$(basename "$service_dir")
        dest_service_dir="$dest_path/$service_name"

        echo "📦 Migrating: $service_name"
        rsync -av "$service_dir/" "$dest_service_dir/"

        if [ $? -eq 0 ]; then
            echo "✅ Successfully migrated: $service_name"
        else
            echo "❌ Failed to migrate: $service_name"
        fi
    done

    echo "✅ Volume migration completed"
    return 0
}

# Function: check_volume_permissions
# Description: Validates volume permissions and ownership
# Arguments: None
# Returns: 0 if valid, 1 if issues found
check_volume_permissions() {
    load_volume_config

    echo "🔐 Checking volume permissions..."

    if [ ! -d "$VOLUME_BASE_PATH" ]; then
        echo "⚠️  Volume base path does not exist: $VOLUME_BASE_PATH"
        return 1
    fi

    local issues=0

    # Check permissions for each volume directory
    find "$VOLUME_BASE_PATH" -mindepth 2 -maxdepth 2 -type d | while read -r volume_dir; do
        # Get current permissions and ownership
        current_perms=$(stat -c "%a" "$volume_dir" 2>/dev/null)
        current_owner=$(stat -c "%U" "$volume_dir" 2>/dev/null)
        current_group=$(stat -c "%G" "$volume_dir" 2>/dev/null)

        relative_path=$(echo "$volume_dir" | sed "s|$VOLUME_BASE_PATH/||")

        # Check if permissions match expected
        if [ "$current_perms" != "$VOLUME_PERMISSIONS" ]; then
            echo "⚠️  Incorrect permissions: $relative_path ($current_perms, expected $VOLUME_PERMISSIONS)"
            issues=$((issues + 1))
        fi

        # Check ownership (if we can determine expected owner name)
        if command -v getent >/dev/null 2>&1; then
            expected_owner=$(getent passwd "$VOLUME_OWNER" | cut -d: -f1)
            expected_group=$(getent group "$VOLUME_GROUP" | cut -d: -f1)

            if [ -n "$expected_owner" ] && [ "$current_owner" != "$expected_owner" ]; then
                echo "⚠️  Incorrect owner: $relative_path ($current_owner, expected $expected_owner)"
                issues=$((issues + 1))
            fi

            if [ -n "$expected_group" ] && [ "$current_group" != "$expected_group" ]; then
                echo "⚠️  Incorrect group: $relative_path ($current_group, expected $expected_group)"
                issues=$((issues + 1))
            fi
        fi
    done

    if [ $issues -eq 0 ]; then
        echo "✅ Volume permissions are valid"
        return 0
    else
        echo "❌ Found $issues permission issues"
        echo "💡 Run 'create_volume_directories' to fix permissions"
        return 1
    fi
}

# Function: generate_compose_with_volumes
# Description: Generates docker-compose.yaml with proper volume paths
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_compose_with_volumes() {
    # Load volume paths
    generate_volume_paths > /dev/null

    # Source volume environment
    if [ -f "$VOLUMES_ENV_FILE" ]; then
        # shellcheck source=/dev/null
        source "$VOLUMES_ENV_FILE"
    fi

    # Load service generator if available
    if [ -f "$PROJECT_ROOT/scripts/service_generator.sh" ]; then
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/scripts/service_generator.sh"
        generate_compose_from_services
    else
        echo "❌ Error: Service generator not found"
        return 1
    fi
}

# Export functions for testing
export -f load_volume_config
export -f generate_volume_paths
export -f validate_volume_config
export -f setup_nfs_mount
export -f create_volume_directories
export -f generate_backup_config
export -f show_volume_usage
export -f migrate_volumes
export -f check_volume_permissions
export -f generate_compose_with_volumes
