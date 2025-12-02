#!/bin/bash
set -euo pipefail

# Main CLI Entry Point
# Routes commands to orchestrator-specific CLIs

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)


# Colors
COLOR_RESET='\033[0m'
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'
COLOR_BOLD='\033[1m'

show_usage() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}Homelab CLI${COLOR_RESET} - Multi-orchestrator deployment tool"
  echo ""
  echo -e "${COLOR_BOLD}USAGE:${COLOR_RESET}"
  echo -e "  $0 <command> [options]"
  echo ""
  echo -e "${COLOR_BOLD}COMMANDS:${COLOR_RESET}"
  echo -e "  ${COLOR_GREEN}deploy${COLOR_RESET}              Deploy all services"
  echo -e "  ${COLOR_GREEN}cluster init${COLOR_RESET}        Initialize cluster"
  echo -e "  ${COLOR_GREEN}cluster status${COLOR_RESET}      Show cluster status"
  echo -e "  ${COLOR_GREEN}teardown${COLOR_RESET}            Complete cleanup (nuke)"
  echo -e "  ${COLOR_GREEN}help${COLOR_RESET}                Show this help message"
  echo ""
  echo -e "${COLOR_BOLD}OPTIONS:${COLOR_RESET}"
  echo -e "  ${COLOR_YELLOW}--orchestrator TYPE${COLOR_RESET} Specify orchestrator (swarm|kubernetes) [default: swarm]"
  echo -e "  ${COLOR_YELLOW}--help, -h${COLOR_RESET}          Show this help message"
  echo ""
  echo -e "${COLOR_BOLD}EXAMPLES:${COLOR_RESET}"
  echo -e "  ${COLOR_BLUE}$0 deploy${COLOR_RESET}                          # Deploy using Docker Swarm (default)"
  echo -e "  ${COLOR_BLUE}$0 cluster init${COLOR_RESET}                    # Initialize Docker Swarm cluster"
  echo -e "  ${COLOR_BLUE}$0 teardown${COLOR_RESET}                        # Complete cluster teardown"
  echo -e "  ${COLOR_BLUE}$0 deploy --orchestrator kubernetes${COLOR_RESET} # Deploy using Kubernetes (future)"
  echo ""
}

# Default orchestrator
ORCHESTRATOR="${ORCHESTRATOR:-swarm}"

# Parse global options
while [[ $# -gt 0 ]]; do
  case $1 in
    --orchestrator)
      ORCHESTRATOR="$2"
      shift 2
      ;;
    --help|-h|help)
      show_usage
      exit 0
      ;;
    *)
      # Not a global option, break to pass to orchestrator CLI
      break
      ;;
  esac
done

# Validate orchestrator
case "$ORCHESTRATOR" in
  swarm|docker_swarm)
    ORCHESTRATOR_CLI="$SCRIPT_DIR/docker_swarm/cli.sh"
    ;;
  kubernetes|k8s)
    ORCHESTRATOR_CLI="$SCRIPT_DIR/kubernetes/cli.sh"
    if [[ ! -f "$ORCHESTRATOR_CLI" ]]; then
      echo -e "${COLOR_RED}Error: Kubernetes support not yet implemented${COLOR_RESET}" >&2
      exit 1
    fi
    ;;
  *)
    echo -e "${COLOR_RED}Error: Unknown orchestrator '$ORCHESTRATOR'${COLOR_RESET}" >&2
    echo -e "Supported orchestrators: swarm, kubernetes" >&2
    exit 1
    ;;
esac

# Check if orchestrator CLI exists
if [[ ! -f "$ORCHESTRATOR_CLI" ]]; then
  echo -e "${COLOR_RED}Error: Orchestrator CLI not found at $ORCHESTRATOR_CLI${COLOR_RESET}" >&2
  exit 1
fi

# Delegate to orchestrator-specific CLI
exec "$ORCHESTRATOR_CLI" "$@"
