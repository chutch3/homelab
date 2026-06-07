# Devbox SSH & Dev Environment Design

**Date:** 2026-06-07
**Status:** Approved

## Goal

Evolve the `code-server` stack into a fully self-contained, SSH-accessible dev machine. The browser IDE (code.diyhub.dev) remains the primary interface, but SSH access enables native terminal clients, VS Code Remote SSH, and persistent sessions via tmux — without depending on claudecodeui or any web-based terminal wrapper.

## Out of Scope

- mosh — ruled out because all traffic enters via Traefik (TCP only); UDP cannot be proxied through it
- claudecodeui changes — left as-is for now
- New SSH key generation — the existing homelab key is reused for both outbound and inbound SSH

---

## 1. Image Changes (`images/devbox/Dockerfile`)

### New packages (added to the apt install block)

- `openssh-server` — inbound SSH daemon
- `supervisor` — process manager for running sshd + code-server independently

### New binary: MinIO client (`mc`)

Installed as a static binary using the same pattern as `kubectl` and `yq`:

```dockerfile
RUN curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc \
        -o /usr/local/bin/mc && chmod +x /usr/local/bin/mc
```

### supervisord config (baked into image)

File: `/etc/supervisor/conf.d/devbox.conf`

```ini
[supervisord]
nodaemon=true

[program:sshd]
command=/usr/sbin/sshd -D -e
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:code-server]
command=code-server --auth none --bind-addr 0.0.0.0:3001 /home/coder/workspace
user=coder
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

`sshd` runs as root (required). `code-server` drops to uid `coder` via the `user=` directive.

### sshd config (baked into image)

File: `/etc/ssh/sshd_config.d/devbox.conf`

```
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
AllowUsers coder
```

### Entrypoint change

The `user: "1000:1000"` override is removed from docker-compose (supervisord must start as root to launch sshd). The image's existing `ENTRYPOINT ["/usr/bin/dumb-init", "--"]` is kept. `CMD` changes to:

```dockerfile
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/devbox.conf"]
```

### Pre-create SSH dirs

Add to the existing `RUN mkdir -p ...` line:

```
/var/run/sshd
```

(Required by sshd at startup.)

---

## 2. docker-compose Changes (`stacks/apps/code-server/docker-compose.yml`)

### Remove

```yaml
user: "1000:1000"
```

### Add environment variables

```yaml
environment:
  - GIT_AUTHOR_NAME=${GIT_AUTHOR_NAME}
  - GIT_AUTHOR_EMAIL=${GIT_AUTHOR_EMAIL}
  - GIT_COMMITTER_NAME=${GIT_AUTHOR_NAME}
  - GIT_COMMITTER_EMAIL=${GIT_AUTHOR_EMAIL}
```

Git respects these env vars natively — no gitconfig file needed.

### Add port

```yaml
ports:
  - target: 22
    published: 2222
    protocol: tcp
    mode: ingress
```

### Add Traefik TCP labels

```yaml
- "traefik.tcp.routers.codeserver-ssh.rule=HostSNI(`*`)"
- "traefik.tcp.routers.codeserver-ssh.entrypoints=ssh"
- "traefik.tcp.routers.codeserver-ssh.service=codeserver-ssh"
- "traefik.tcp.services.codeserver-ssh.loadbalancer.server.port=22"
```

### Add `.claude` volume

The `.claude` volume is currently only mounted in the claudecodeui stack. It must also be mounted in code-server so Claude Code sessions persist when used via SSH or the web terminal.

```yaml
volumes:
  - claude_config:/home/coder/.claude
```

With corresponding volume definition pointing at the same iSCSI path:

```yaml
claude_config:
  driver: local
  driver_opts:
    type: "none"
    o: "bind"
    device: "/mnt/iscsi/app-data/dev-env/ai-configs/claude"
```

---

## 3. pre-flight / hooks.sh Changes

### `hooks.sh` — `pre_deploy()`

Add after the existing key copy block:

```bash
local auth_keys="$ssh_dest/authorized_keys"
if [[ ! -f "$auth_keys" ]] && [[ -f "$ssh_dest/${ssh_key_name}.pub" ]]; then
    cp "$ssh_dest/${ssh_key_name}.pub" "$auth_keys"
    chmod 600 "$auth_keys"
    chown 1000:1000 "$auth_keys"
fi
```

This bootstraps `authorized_keys` from the homelab public key on first deploy only. Subsequent runs leave the file untouched so manually added keys are preserved.

---

## 4. Reverse-Proxy Stack Changes (`stacks/reverse-proxy/docker-compose.yml`)

### Add Traefik SSH entrypoint

To the Traefik `command:` block, add:

```
--entrypoints.ssh.address=:2222
```

### Publish port 2222

```yaml
ports:
  - target: 2222
    published: 2222
    protocol: tcp
    mode: ingress
```

---

## 5. `.env.example` Additions

```bash
# Dev environment — git identity
GIT_AUTHOR_NAME=Your Name
GIT_AUTHOR_EMAIL=you@example.com
```

---

## 6. GPU Access

No changes required. The existing compose config (`NVIDIA_VISIBLE_DEVICES=all`, `NVIDIA_DRIVER_CAPABILITIES=compute,utility`, placement on `node.labels.gpu == true`) is correct.

**Prerequisite (host-level):** The GPU node must have `nvidia-container-runtime` configured as the default Docker runtime in `/etc/docker/daemon.json`. This is a one-time host setup, not a container concern.

---

## 7. Client SSH Config (laptop)

After deployment, add to `~/.ssh/config` on your local machine:

```
Host devbox
    HostName code.diyhub.dev
    Port 2222
    User coder
    IdentityFile ~/.ssh/homelab_rsa
```

Then: `ssh devbox`

---

## Summary of Files Changed

| File | Change |
|------|--------|
| `images/devbox/Dockerfile` | Add openssh-server, supervisor, mc; add sshd + supervisord configs; update CMD; mkdir /var/run/sshd |
| `stacks/apps/code-server/docker-compose.yml` | Remove user override; add git env vars, port 2222, Traefik TCP labels, claude_config volume |
| `stacks/apps/code-server/hooks.sh` | Bootstrap authorized_keys from .pub on first deploy |
| `stacks/reverse-proxy/docker-compose.yml` | Add Traefik ssh entrypoint + publish port 2222 |
| `.env.example` | Add GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL |
