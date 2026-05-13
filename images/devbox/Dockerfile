FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# All system packages in one layer — alphabetically sorted for easy maintenance
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    dumb-init \
    fzf \
    git \
    git-lfs \
    gnupg \
    htop \
    jq \
    libbz2-dev \
    libffi-dev \
    liblzma-dev \
    libncurses-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libxml2-dev \
    libxmlsec1-dev \
    llvm \
    locales \
    lsb-release \
    openssh-client \
    procps \
    sudo \
    tk-dev \
    tmux \
    unzip \
    vim \
    wget \
    xz-utils \
    zip \
    zlib1g-dev \
    zsh \
    && locale-gen en_US.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI and Docker CLI (both require signed apt repos)
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
        | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && apt-get install -y --no-install-recommends gh docker-ce-cli docker-compose-plugin \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# kubectl and yq as static binaries (avoids extra apt sources)
RUN KUBECTL_VERSION=$(curl -fsSL https://dl.k8s.io/release/stable.txt) && \
    curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
        -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl && \
    YQ_VERSION=$(curl -fsSL https://api.github.com/repos/mikefarah/yq/releases/latest | jq -r .tag_name) && \
    curl -fsSL "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
        -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq

# Create coder user and install code-server — last root operations before user switch
RUN userdel -r ubuntu && \
    useradd -m -u 1000 -s /bin/bash coder && \
    echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    curl -fsSL https://code-server.dev/install.sh | sh

# --- Single user switch; everything below runs as coder ---
USER coder
WORKDIR /home/coder
ENV HOME=/home/coder

# fnm + Node 22
RUN curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir "$HOME/.local/share/fnm" --skip-shell
ENV PATH="$HOME/.local/share/fnm:$PATH"
RUN eval "$(fnm env --use-on-cd)" && fnm install 22 && fnm default 22

# uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="$HOME/.local/bin:$PATH"

# pyenv
RUN curl https://pyenv.run | bash
ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

# Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
ENV PATH="$HOME/.cargo/bin:$PATH"

# .NET SDK (LTS)
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel LTS --install-dir "$HOME/.dotnet"
ENV PATH="$HOME/.dotnet:$HOME/.dotnet/tools:$PATH"
ENV DOTNET_ROOT="$HOME/.dotnet"
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1

# npm global tools
RUN eval "$(fnm env --use-on-cd)" && \
    npm install -g @anthropic-ai/claude-code@latest @google/gemini-cli@latest @cloudcli-ai/cloudcli@latest

# Ansible via uv (isolated, up-to-date)
RUN uv tool install ansible

# Forge Code
RUN curl -fsSL https://forgecode.dev/install.sh | bash

# Shell configuration — done last so all tools are present
# hadolint ignore=SC2016
RUN echo 'export PATH="$HOME/.local/share/fnm:$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.pyenv/bin:$HOME/.dotnet:$HOME/.dotnet/tools:$PATH"' >> ~/.bashrc && \
    echo 'export DOTNET_ROOT="$HOME/.dotnet"'                                                                                                    >> ~/.bashrc && \
    echo 'export DOTNET_CLI_TELEMETRY_OPTOUT=1'                                                                                                  >> ~/.bashrc && \
    echo 'export PYENV_ROOT="$HOME/.pyenv"'                                                                                                      >> ~/.bashrc && \
    echo 'eval "$(fnm env --use-on-cd)"'                                                                                                         >> ~/.bashrc && \
    echo '[ -f /usr/share/doc/fzf/examples/key-bindings.bash ] && source /usr/share/doc/fzf/examples/key-bindings.bash'                         >> ~/.bashrc

# Pre-create volume mount points with correct ownership
RUN mkdir -p ~/.claude ~/.config/gemini ~/.cloudcli ~/.forge ~/.ssh ~/.local/share/code-server

ENV PORT=3001
ENV NODE_ENV=production
ENV VITE_IS_PLATFORM=true

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["/bin/bash", "-c", "cloudcli start"]
