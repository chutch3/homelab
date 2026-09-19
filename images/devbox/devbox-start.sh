#!/usr/bin/env bash
set -euo pipefail

mkdir -p /run/sshd
SSH_DIR="/home/coder/.ssh"
mkdir -p "$SSH_DIR"
chown 1000:1000 "$SSH_DIR"
chmod 700 "$SSH_DIR"

# Restore host keys from volume, or generate and persist them on first boot.
# Storing in the volume prevents "host key changed" warnings on redeploy.
if [[ -f "${SSH_DIR}/ssh_host_ed25519_key" ]]; then
    for key_file in "${SSH_DIR}"/ssh_host_*; do
        cp "$key_file" /etc/ssh/
    done
else
    ssh-keygen -A
    for key_file in /etc/ssh/ssh_host_*; do
        cp "$key_file" "${SSH_DIR}/"
    done
    chown 1000:1000 "${SSH_DIR}"/ssh_host_*
fi
chmod 600 /etc/ssh/ssh_host_*_key
chmod 644 /etc/ssh/ssh_host_*_key.pub

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/devbox.conf
