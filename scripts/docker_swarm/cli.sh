#!/bin/bash
set -euo pipefail

# Docker Swarm CLI
# Handles Docker Swarm-specific commands

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)


# Colors
COLOR_RESET='\033[0m'
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'
COLOR_BOLD='\033[1m'

show_usage() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}Docker Swarm CLI${COLOR_RESET}"
  echo ""
  echo -e "${COLOR_BOLD}USAGE:${COLOR_RESET}"
  echo -e "  $0 <command> [options]"
  echo ""
  echo -e "${COLOR_BOLD}COMMANDS:${COLOR_RESET}"
  echo -e "  ${COLOR_GREEN}deploy [options]${COLOR_RESET}       Deploy services to swarm"
  echo -e "  ${COLOR_GREEN}cluster init${COLOR_RESET}           Initialize Docker Swarm cluster"
  echo -e "  ${COLOR_GREEN}cluster status${COLOR_RESET}         Show cluster status"
  echo -e "  ${COLOR_GREEN}cluster join <node>${COLOR_RESET}    Join node to cluster"
  echo -e "  ${COLOR_GREEN}volume ls [service]${COLOR_RESET}    List Docker volumes"
  echo -e "  ${COLOR_GREEN}volume inspect <service>${COLOR_RESET}  Inspect volumes for a service"
  echo -e "  ${COLOR_GREEN}volume diff <service>${COLOR_RESET}     Compare volume config (current vs compose)"
  echo -e "  ${COLOR_GREEN}volume recreate <service>${COLOR_RESET}  Recreate volumes (stops service, removes volumes)"
  echo -e "  ${COLOR_GREEN}teardown [options]${COLOR_RESET}    Complete cluster teardown or single stack"
  echo -e "  ${COLOR_GREEN}help${COLOR_RESET}                   Show this help message"
  echo ""
  echo -e "${COLOR_BOLD}EXAMPLES:${COLOR_RESET}"
  echo -e "  ${COLOR_BLUE}$0 deploy${COLOR_RESET}                        # Deploy all services"
  echo -e "  ${COLOR_BLUE}$0 cluster init${COLOR_RESET}                  # Initialize swarm cluster"
  echo -e "  ${COLOR_BLUE}$0 cluster status${COLOR_RESET}                # Show cluster status"
  echo -e "  ${COLOR_BLUE}$0 teardown${COLOR_RESET}                      # Complete cluster teardown"
  echo -e "  ${COLOR_BLUE}$0 teardown --stack sonarr${COLOR_RESET}       # Teardown sonarr stack only"
  echo -e "  ${COLOR_BLUE}$0 teardown --stack sonarr --dry-run${COLOR_RESET}  # Preview teardown"
  echo ""
}

# Parse command
COMMAND="${1:-}"

case "$COMMAND" in
  deploy)
    shift
    # Check for help flag
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
      echo -e "${COLOR_BOLD}${COLOR_GREEN}DEPLOY COMMAND${COLOR_RESET}"
      echo ""
      echo -e "${COLOR_BOLD}USAGE:${COLOR_RESET}"
      echo -e "  $0 deploy [options]"
      echo ""
      echo -e "${COLOR_BOLD}OPTIONS:${COLOR_RESET}"
      echo -e "  ${COLOR_YELLOW}--skip-apps <apps>${COLOR_RESET}    Comma-separated list of apps to skip"
      echo -e "  ${COLOR_YELLOW}--only-apps <apps>${COLOR_RESET}    Deploy only these apps"
      echo -e "  ${COLOR_YELLOW}--help, -h${COLOR_RESET}             Show this help"
      echo ""
      exit 0
    fi
    # Delegate to deploy.sh
    exec "$SCRIPT_DIR/deploy.sh" "$@"
    ;;

  cluster)
    SUBCOMMAND="${2:-}"
    shift 2 || true

    case "$SUBCOMMAND" in
      init)
        # Check for help flag
        if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
          echo -e "${COLOR_BOLD}${COLOR_GREEN}CLUSTER INIT COMMAND${COLOR_RESET}"
          echo ""
          echo -e "${COLOR_BOLD}USAGE:${COLOR_RESET}"
          echo -e "  $0 cluster init [options]"
          echo ""
          echo -e "${COLOR_BOLD}OPTIONS:${COLOR_RESET}"
          echo -e "  ${COLOR_YELLOW}-c, --config FILE${COLOR_RESET}    Config file path [default: machines.yaml]"
          echo -e "  ${COLOR_YELLOW}--help, -h${COLOR_RESET}            Show this help"
          echo ""
          exit 0
        fi
        # Delegate to cluster.sh
        exec "$SCRIPT_DIR/cluster.sh" init-cluster "$@"
        ;;

      status)
        # Check for help flag
        if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
          echo -e "${COLOR_BOLD}${COLOR_GREEN}CLUSTER STATUS COMMAND${COLOR_RESET}"
          echo ""
          echo -e "${COLOR_BOLD}USAGE:${COLOR_RESET}"
          echo -e "  $0 cluster status"
          echo ""
          exit 0
        fi
        # Delegate to cluster.sh
        exec "$SCRIPT_DIR/cluster.sh" monitor-cluster "$@"
        ;;

      join)
        # Delegate to cluster.sh
        exec "$SCRIPT_DIR/cluster.sh" join-worker "$@"
        ;;

      *)
        echo -e "${COLOR_RED}Error: Unknown cluster subcommand '$SUBCOMMAND'${COLOR_RESET}" >&2
        echo -e "Available subcommands: init, status, join" >&2
        exit 1
        ;;
    esac
    ;;

  volume)
    SUBCOMMAND="${2:-ls}"
    shift
    shift || true
    # Delegate to volume.sh
    # shellcheck source=volume.sh
    source "$SCRIPT_DIR/volume.sh"
    case "$SUBCOMMAND" in
      ls)
        volume_ls "$@"
        ;;
      inspect)
        volume_inspect "$@"
        ;;
      diff)
        volume_diff "$@"
        ;;
      recreate)
        volume_recreate "$@"
        ;;
      *)
        echo -e "${COLOR_RED}Error: Unknown volume subcommand '$SUBCOMMAND'${COLOR_RESET}" >&2
        echo -e "Available subcommands: ls, inspect, diff, recreate" >&2
        exit 1
        ;;
    esac
    ;;

  teardown)
    shift
    # Check for help flag
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
      echo -e "${COLOR_BOLD}${COLOR_GREEN}TEARDOWN COMMAND${COLOR_RESET}"
      echo ""
      echo -e "${COLOR_BOLD}USAGE:${COLOR_RESET}"
      echo -e "  $0 teardown [options]"
      echo ""
      echo -e "${COLOR_BOLD}OPTIONS:${COLOR_RESET}"
      echo -e "  ${COLOR_YELLOW}--stack <name>${COLOR_RESET}       Teardown specific stack and clean volumes on all nodes"
      echo -e "  ${COLOR_YELLOW}--dry-run${COLOR_RESET}            Show what would be removed (requires --stack)"
      echo -e "  ${COLOR_YELLOW}--help, -h${COLOR_RESET}           Show this help"
      echo ""
      echo -e "${COLOR_BOLD}EXAMPLES:${COLOR_RESET}"
      echo -e "  ${COLOR_BLUE}$0 teardown${COLOR_RESET}                      # Complete cluster teardown"
      echo -e "  ${COLOR_BLUE}$0 teardown --stack sonarr${COLOR_RESET}       # Remove sonarr and clean volumes"
      echo -e "  ${COLOR_BLUE}$0 teardown --stack sonarr --dry-run${COLOR_RESET}  # Preview what would be removed"
      echo ""
      echo -e "${COLOR_BOLD}WARNING:${COLOR_RESET}"
      echo -e "  ${COLOR_RED}Full teardown will completely destroy the cluster and all data!${COLOR_RESET}"
      echo ""
      exit 0
    fi
    # Delegate to teardown.sh
    exec "$SCRIPT_DIR/teardown.sh" "$@"
    ;;

  --help|-h|help|"")
    show_usage
    exit 0
    ;;

  *)
    echo -e "${COLOR_RED}Error: Unknown command '$COMMAND'${COLOR_RESET}" >&2
    echo "" >&2
    show_usage >&2
    exit 1
    ;;
esac
