#!/usr/bin/env bash
set -euo pipefail

hook_mode() {
    case "$1" in
        pre_deploy) echo "root" ;;
        *)          echo "user" ;;
    esac
}

pre_deploy() {
    local dev_env_root="/mnt/iscsi/app-data/dev-env"
    local real_user="${SUDO_USER:-$USER}"
    local real_home
    real_home=$(eval echo "~${real_user}")
    local ssh_key_name
    ssh_key_name="$(basename "${SSH_KEY_FILE:-${real_home}/.ssh/homelab_rsa}")"
    local ssh_key_src="${SSH_KEY_FILE:-${real_home}/.ssh/homelab_rsa}"
    local ssh_dest="${dev_env_root}/shared-ssh"

    mkdir -p "${dev_env_root}/workspace" \
             "${dev_env_root}/code-server/config" \
             "${dev_env_root}/shared-ssh" \
             "${dev_env_root}/ai-configs/claude" \
             "${dev_env_root}/ai-configs/gemini" \
             "${dev_env_root}/ai-configs/cloudcli" \
             "${dev_env_root}/ai-configs/forge"
    chown -R 1000:1000 "$dev_env_root"
    chmod 700 "$ssh_dest"

    if [[ -f "$ssh_key_src" ]]; then
        cp "$ssh_key_src" "$ssh_dest/$ssh_key_name"
        chmod 600 "$ssh_dest/$ssh_key_name"
        chown 1000:1000 "$ssh_dest/$ssh_key_name"
        if [[ -f "${ssh_key_src}.pub" ]]; then
            cp "${ssh_key_src}.pub" "$ssh_dest/${ssh_key_name}.pub"
            chmod 644 "$ssh_dest/${ssh_key_name}.pub"
            chown 1000:1000 "$ssh_dest/${ssh_key_name}.pub"
        fi
    fi

    local auth_keys="$ssh_dest/authorized_keys"
    if [[ ! -f "$auth_keys" ]] && [[ -f "$ssh_dest/${ssh_key_name}.pub" ]]; then
        cp "$ssh_dest/${ssh_key_name}.pub" "$auth_keys"
        chmod 600 "$auth_keys"
        chown 1000:1000 "$auth_keys"
    fi

    local domain_pattern="${BASE_DOMAIN:+*.${BASE_DOMAIN}}"
    local ssh_host_pattern="192.168.* 10.* ${domain_pattern} ${SSH_EXTRA_HOSTS:-}"
    cat > "$ssh_dest/config" <<EOF
Host ${ssh_host_pattern}
    StrictHostKeyChecking accept-new
    IdentityFile ~/.ssh/${ssh_key_name}

Host *
    StrictHostKeyChecking accept-new
EOF
    chmod 644 "$ssh_dest/config"
    chown 1000:1000 "$ssh_dest/config"
}

post_deploy() { :; }

case "${1:-}" in
    hook_mode)   hook_mode "${2:-}" ;;
    pre_deploy)  pre_deploy ;;
    post_deploy) post_deploy ;;
    *) echo "Usage: $0 {pre_deploy|post_deploy}" >&2; exit 1 ;;
esac
