#!/bin/bash
# Homelab Configuration Schema Validator
# Validates homelab.yaml against JSON schema

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEMA_FILE="$PROJECT_ROOT/schemas/homelab-schema.json"
DEFAULT_CONFIG="$PROJECT_ROOT/homelab.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] [CONFIG_FILE]

Validate homelab.yaml configuration against JSON schema.

OPTIONS:
    -h, --help          Show this help message
    -s, --schema FILE   Path to schema file (default: schemas/homelab-schema.json)
    -q, --quiet         Quiet mode - only show errors
    -v, --verbose       Verbose mode - show detailed validation info

ARGUMENTS:
    CONFIG_FILE         Path to homelab.yaml file (default: homelab.yaml)

EXAMPLES:
    $0                                  # Validate default homelab.yaml
    $0 examples/homelab-basic.yaml     # Validate specific example
    $0 -v homelab.yaml                 # Verbose validation

EOF
}

# Parse command line arguments
QUIET=0
VERBOSE=0
CONFIG_FILE=""
CUSTOM_SCHEMA=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -s|--schema)
            CUSTOM_SCHEMA="$2"
            shift 2
            ;;
        -q|--quiet)
            QUIET=1
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            usage >&2
            exit 1
            ;;
        *)
            if [[ -z "$CONFIG_FILE" ]]; then
                CONFIG_FILE="$1"
            else
                echo -e "${RED}Error: Too many arguments${NC}" >&2
                usage >&2
                exit 1
            fi
            shift
            ;;
    esac
done

# Set defaults
CONFIG_FILE="${CONFIG_FILE:-$DEFAULT_CONFIG}"
SCHEMA_FILE="${CUSTOM_SCHEMA:-$SCHEMA_FILE}"

# Logging functions
log_info() {
    if [[ $QUIET -eq 0 ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ $QUIET -eq 0 ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_verbose() {
    if [[ $VERBOSE -eq 1 && $QUIET -eq 0 ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v yq >/dev/null 2>&1; then
        missing_deps+=("yq")
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps+=("python3")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and try again"
        exit 1
    fi
}

# Validate file exists and is readable
validate_file_access() {
    local file="$1"
    local description="$2"

    if [[ ! -f "$file" ]]; then
        log_error "$description not found: $file"
        return 1
    fi

    if [[ ! -r "$file" ]]; then
        log_error "$description not readable: $file"
        return 1
    fi

    return 0
}

# Validate YAML syntax
validate_yaml_syntax() {
    local config_file="$1"

    log_verbose "Checking YAML syntax..."

    if ! yq . "$config_file" >/dev/null 2>&1; then
        log_error "Invalid YAML syntax in $config_file"
        return 1
    fi

    log_verbose "YAML syntax is valid"
    return 0
}

# Validate against JSON schema using Python
validate_json_schema() {
    local config_file="$1"
    local schema_file="$2"

    log_verbose "Validating against JSON schema..."

    # Create temporary Python script for validation
    local temp_script
    temp_script=$(mktemp)
    trap 'rm -f "$temp_script"' EXIT

    cat > "$temp_script" << 'EOF'
import json
import yaml
import sys
from jsonschema import validate, ValidationError, Draft7Validator

def main():
    config_file = sys.argv[1]
    schema_file = sys.argv[2]
    verbose = len(sys.argv) > 3 and sys.argv[3] == "--verbose"

    try:
        # Load schema
        with open(schema_file, 'r') as f:
            schema = json.load(f)

        # Load and parse YAML config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Validate
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(config))

        if errors:
            print("Schema validation failed:")
            for error in errors:
                path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
                print(f"  Path: {path}")
                print(f"  Error: {error.message}")
                if verbose and error.context:
                    for context_error in error.context:
                        print(f"    Context: {context_error.message}")
                print()
            sys.exit(1)
        else:
            if verbose:
                print("Schema validation passed - all required fields present and valid")
            sys.exit(0)

    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON schema parsing error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

    # Run validation
    local python_args=("$config_file" "$schema_file")
    if [[ $VERBOSE -eq 1 ]]; then
        python_args+=("--verbose")
    fi

    if python3 "$temp_script" "${python_args[@]}" 2>&1; then
        log_verbose "JSON schema validation passed"
        return 0
    else
        log_error "JSON schema validation failed"
        return 1
    fi
}

# Perform additional semantic checks
validate_semantic_rules() {
    local config_file="$1"

    log_verbose "Performing semantic validation..."

    local errors=0

    # Check that deployment type matches machine count
    local deployment
    deployment=$(yq '.deployment' "$config_file")
    local machine_count
    machine_count=$(yq '.machines | length' "$config_file")

    if [[ "$deployment" == "docker_compose" && $machine_count -gt 1 ]]; then
        log_verbose "Multi-machine Docker Compose deployment detected"
    elif [[ "$deployment" == "docker_swarm" && $machine_count -eq 1 ]]; then
        log_warning "Single machine Docker Swarm deployment - consider docker_compose instead"
    fi

    # Check for port conflicts
    local ports
    ports=$(yq '.services[].port // empty' "$config_file" 2>/dev/null | sort)
    local duplicate_ports
    duplicate_ports=$(echo "$ports" | uniq -d)

    if [[ -n "$duplicate_ports" ]]; then
        log_error "Duplicate ports detected: $duplicate_ports"
        ((errors++))
    fi

    # Check machine references in deploy fields
    local machine_names
    machine_names=$(yq '.machines | keys | .[]' "$config_file" 2>/dev/null)
    local deploy_targets
    deploy_targets=$(yq '.services[].deploy // empty' "$config_file" 2>/dev/null | grep -v '^(driver|all|random|any)$' || true)

    while read -r target; do
        if [[ -n "$target" ]]; then
            if ! echo "$machine_names" | grep -q "^$target$"; then
                log_error "Service deploy target '$target' does not match any machine name"
                ((errors++))
            fi
        fi
    done <<< "$deploy_targets"

    log_verbose "Semantic validation completed with $errors errors"
    return $errors
}

# Main validation function
main() {
    log_info "Starting homelab.yaml validation"
    log_verbose "Config file: $CONFIG_FILE"
    log_verbose "Schema file: $SCHEMA_FILE"

    # Check dependencies
    check_dependencies

    # Validate file access
    validate_file_access "$CONFIG_FILE" "Configuration file" || exit 1
    validate_file_access "$SCHEMA_FILE" "Schema file" || exit 1

    # Validate YAML syntax
    validate_yaml_syntax "$CONFIG_FILE" || exit 1

    # Validate against JSON schema
    validate_json_schema "$CONFIG_FILE" "$SCHEMA_FILE" || exit 1

    # Perform semantic validation
    if ! validate_semantic_rules "$CONFIG_FILE"; then
        log_error "Semantic validation failed"
        exit 1
    fi

    log_success "homelab.yaml validation completed successfully"

    if [[ $VERBOSE -eq 1 ]]; then
        echo
        log_info "Configuration summary:"
        echo "  Deployment type: $(yq '.deployment' "$CONFIG_FILE")"
        echo "  Machines: $(yq '.machines | length' "$CONFIG_FILE")"
        echo "  Services: $(yq '.services | length' "$CONFIG_FILE")"
        echo "  Enabled services: $(yq '.services | to_entries | map(select(.value.enabled // true)) | length' "$CONFIG_FILE" 2>/dev/null || echo "N/A")"
    fi
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
