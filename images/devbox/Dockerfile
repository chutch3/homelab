# syntax=docker/dockerfile:1
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# apt behaviour: retry flaky downloads, and keep downloaded .debs so the BuildKit
# cache mounts below can serve them on rebuild (Ubuntu's default docker-clean hook
# otherwise deletes them after every install).
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries && \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# Bootstrap tools needed to set up external repos.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg

# Add external apt repos (GitHub CLI, Docker CE).
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && \
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod go+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install everything from apt in a single pass. The BuildKit cache mounts make
# rebuilds fast and let apt reuse already-downloaded .debs, which sidesteps the
# transient zstd/dpkg unpack corruption the old manual retry loop worked around.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        docker-ce-cli \
        docker-compose-plugin \
        dumb-init \
        fzf \
        gh \
        git \
        git-lfs \
        htop \
        jq \
        libssl-dev \
        libuv1-dev \
        libxml2-dev \
        libxmlsec1-dev \
        locales \
        lsb-release \
        openssh-client \
        openssh-server \
        pre-commit \
        procps \
        r-base \
        r-base-dev \
        sudo \
        supervisor \
        tmux \
        unzip \
        vim \
        wget \
        xz-utils \
        zip \
        zlib1g-dev \
        zsh && \
    locale-gen en_US.UTF-8

# kubectl and yq as static binaries (avoids extra apt sources).
# Leave *_VERSION empty to track the latest release, or set it to pin one.
ARG KUBECTL_VERSION=""
ARG YQ_VERSION=""
RUN kver="${KUBECTL_VERSION:-$(curl -fsSL https://dl.k8s.io/release/stable.txt)}" && \
    curl -fsSL "https://dl.k8s.io/release/${kver}/bin/linux/amd64/kubectl" \
        -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl && \
    yver="${YQ_VERSION:-$(curl -fsSL https://api.github.com/repos/mikefarah/yq/releases/latest | jq -r .tag_name)}" && \
    curl -fsSL "https://github.com/mikefarah/yq/releases/download/${yver}/yq_linux_amd64" \
        -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq

# mc (MinIO client) — the former dl.min.io binary endpoint returns HTTP 410.
COPY --from=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727 /usr/bin/mc /usr/local/bin/mc

# Smoke-check the copied mc binary, then install the R languageserver (needed by
# the VS Code R extension; its transitive dep 'fs' links against libuv1-dev).
# The second Rscript makes the build fail loudly — install.packages() returns 0
# even when a dependency fails to compile, which silently shipped a missing
# languageserver for a long time.
RUN mc --version && \
    Rscript -e "install.packages('languageserver', repos='https://cloud.r-project.org')" && \
    Rscript -e "if (!requireNamespace('languageserver', quietly = TRUE)) quit(status = 1)"

# SSH server + supervisor configuration (companion files live in the build context).
RUN rm -f /etc/ssh/ssh_host_* && \
    mkdir -p /etc/ssh/sshd_config.d /etc/supervisor/conf.d
COPY sshd_devbox.conf              /etc/ssh/sshd_config.d/devbox.conf
COPY supervisord.conf             /etc/supervisor/conf.d/devbox.conf
COPY --chmod=0755 devbox-start.sh /usr/local/bin/devbox-start.sh

# Create coder user and install code-server — last root operations before user switch.
# Leave CODE_SERVER_VERSION empty for the latest release, or set it to pin one.
ARG CODE_SERVER_VERSION=""
RUN userdel -r ubuntu && \
    useradd -m -u 1000 -s /bin/bash coder && \
    # Unlock coder so sshd accepts pubkey auth under UsePAM no (password login stays off).
    usermod -p "$(openssl passwd -6 "$(head -c 32 /dev/urandom | base64)")" coder && \
    echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    if [ -n "$CODE_SERVER_VERSION" ]; then \
        curl -fsSL https://code-server.dev/install.sh | sh -s -- --version "$CODE_SERVER_VERSION"; \
    else \
        curl -fsSL https://code-server.dev/install.sh | sh; \
    fi

# --- Single user switch; everything below runs as coder ---
USER coder
WORKDIR /home/coder
ENV HOME=/home/coder

# fnm + Node
ARG NODE_VERSION=22
RUN curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir "$HOME/.local/share/fnm" --skip-shell
ENV PATH="$HOME/.local/share/fnm/aliases/default/bin:$HOME/.local/share/fnm:$PATH"
RUN fnm install "${NODE_VERSION}" && fnm default "${NODE_VERSION}"

# uv (Python package manager) + a managed Python (replaces pyenv).
# Leave UV_VERSION empty for the latest uv release, or set it to pin one.
ARG UV_VERSION=""
ARG PYTHON_VERSION=3.12
RUN if [ -n "$UV_VERSION" ]; then \
        curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh; \
    else \
        curl -LsSf https://astral.sh/uv/install.sh | sh; \
    fi
ENV PATH="$HOME/.local/bin:$PATH"
RUN uv python install "${PYTHON_VERSION}"

# go-task (empty = latest, or pass a tag like v3.40.0 to pin)
ARG GO_TASK_VERSION=""
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin ${GO_TASK_VERSION}

# Rust (RUST_VERSION accepts a channel like "stable" or an exact version like "1.83.0")
ARG RUST_VERSION=stable
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --default-toolchain "${RUST_VERSION}"
ENV PATH="$HOME/.cargo/bin:$PATH"

# .NET SDK
ARG DOTNET_CHANNEL=LTS
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel "${DOTNET_CHANNEL}" --install-dir "$HOME/.dotnet"
ENV PATH="$HOME/.dotnet:$HOME/.dotnet/tools:$PATH"
ENV DOTNET_ROOT="$HOME/.dotnet"
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1

# npm global tools (default latest; pin any of these via build args for reproducible builds)
ARG CLAUDE_CODE_VERSION=latest
ARG GEMINI_CLI_VERSION=latest
ARG CLOUDCLI_VERSION=latest
ARG TYPESCRIPT_VERSION=latest
ARG TASK_MASTER_VERSION=latest
ARG CODEX_VERSION=latest
RUN npm install -g \
        "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
        "@google/gemini-cli@${GEMINI_CLI_VERSION}" \
        "@cloudcli-ai/cloudcli@${CLOUDCLI_VERSION}" \
        "typescript@${TYPESCRIPT_VERSION}" \
        "task-master-ai@${TASK_MASTER_VERSION}" \
        "@openai/codex@${CODEX_VERSION}"

# Forge Code
RUN curl -fsSL https://forgecode.dev/install.sh | bash

# Shell configuration — done last so all tools are present
# hadolint ignore=SC2016
RUN echo 'export PATH="$HOME/.local/share/fnm/aliases/default/bin:$HOME/.local/share/fnm:$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.dotnet:$HOME/.dotnet/tools:$PATH"' >> ~/.bashrc && \
    echo 'export DOTNET_ROOT="$HOME/.dotnet"'                                                                                                    >> ~/.bashrc && \
    echo 'export DOTNET_CLI_TELEMETRY_OPTOUT=1'                                                                                                  >> ~/.bashrc && \
    echo 'eval "$(fnm env --use-on-cd)"'                                                                                                         >> ~/.bashrc && \
    echo '[ -f /usr/share/doc/fzf/examples/key-bindings.bash ] && source /usr/share/doc/fzf/examples/key-bindings.bash'                         >> ~/.bashrc

# Pre-create volume mount points with correct ownership
RUN mkdir -p ~/.claude ~/.config/gemini ~/.cloudcli ~/.forge ~/.ssh ~/.local/share/code-server

ENV PORT=3001
ENV VITE_IS_PLATFORM=true

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["sudo", "-E", "/usr/local/bin/devbox-start.sh"]
