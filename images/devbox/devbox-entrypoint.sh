#!/usr/bin/env bash
set -euo pipefail

# Runs as coder before the code-server sudo/supervisor command or CloudCLI.
# Keep the legacy path for consumers that still read ~/.claude.json.
claude_dir="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
legacy_config="${HOME}/.claude.json"
persistent_config="${claude_dir}/.claude.json"
export CLAUDE_CONFIG_DIR="$claude_dir"

mkdir -p "$claude_dir"
(
    # Both stacks share this directory. Serialize their one-time migrations.
    flock -x 9

    if [[ -L "$persistent_config" || ( -e "$persistent_config" && ! -f "$persistent_config" ) ]]; then
        echo "Expected a regular config file at $persistent_config" >&2
        exit 1
    fi

    if [[ -L "$legacy_config" ]]; then
        if [[ "$(readlink "$legacy_config")" != "$persistent_config" ]]; then
            echo "Unexpected config symlink at $legacy_config; migrate it manually before starting." >&2
            exit 1
        fi
    elif [[ -e "$legacy_config" ]]; then
        if [[ ! -f "$legacy_config" ]]; then
            echo "Expected a regular config file at $legacy_config" >&2
            exit 1
        fi

        if [[ ! -e "$persistent_config" ]]; then
            # Publish a complete file atomically so an interrupted copy cannot
            # become the canonical config on the next startup.
            migration_file="$(mktemp "${claude_dir}/.claude.json.migrating.XXXXXX")"
            cp -- "$legacy_config" "$migration_file"
            chmod 600 "$migration_file"
            mv -- "$migration_file" "$persistent_config"
        elif ! cmp -s -- "$legacy_config" "$persistent_config"; then
            # Shared state wins; keep differing local state for reconciliation.
            backup_file="$(mktemp "${claude_dir}/.claude.json.pre-migration.XXXXXX")"
            cp -- "$legacy_config" "$backup_file"
            chmod 600 "$backup_file"
            echo "Preserved differing Claude config at $backup_file" >&2
        fi

        rm -- "$legacy_config"
    fi

    if [[ ! -L "$legacy_config" ]]; then
        ln -s -- "$persistent_config" "$legacy_config"
    fi
) 9> "${claude_dir}/.devbox-config.lock"

exec "$@"
