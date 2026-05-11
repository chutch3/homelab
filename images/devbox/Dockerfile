FROM ubuntu:24.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

# Step 1: Install core system utilities and locales
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    locales \
    procps \
    sudo \
    wget \
    vim \
    unzip \
    zip \
    && locale-gen en_US.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Step 2: Install development and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    git-lfs \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    llvm \
    libncurses-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    dumb-init \
    htop \
    zsh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create generic user 'coder' with UID 1000
RUN userdel -r ubuntu && \
    useradd -m -u 1000 -s /bin/bash coder && \
    echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER coder
WORKDIR /home/coder
ENV HOME=/home/coder

# Install fnm (Node Version Manager)
RUN curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir "$HOME/.local/share/fnm" --skip-shell
ENV PATH="$HOME/.local/share/fnm:$PATH"
RUN eval "$(fnm env --use-on-cd)" && fnm install 22 && fnm default 22

# Add common paths to bashrc
RUN echo "export PATH=\"\$HOME/.local/share/fnm:\$HOME/.local/bin:\$HOME/.cargo/bin:\$HOME/.pyenv/bin:\$PATH\"" >> ~/.bashrc && \
    echo "eval \"\$(fnm env --use-on-cd)\"" >> ~/.bashrc

# Install Node-based tools (Claude, Gemini, CloudCLI)
# We use fnm exec to ensure the correct node version is used for installation
RUN eval "$(fnm env --use-on-cd)" && \
    npm install -g @anthropic-ai/claude-code@latest @google/gemini-cli@latest @cloudcli-ai/cloudcli@latest

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install GitHub CLI (gh)
USER root
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && \
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && apt-get install -y --no-install-recommends gh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
USER coder

# Install pyenv
RUN curl https://pyenv.run | bash
ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

# Install Forge Code
RUN curl -fsSL https://forgecode.dev/install.sh | bash

# Install code-server
USER root
RUN curl -fsSL https://code-server.dev/install.sh | sh
USER coder

# Final environment setup
ENV PORT=3001
ENV NODE_ENV=production
ENV VITE_IS_PLATFORM=true

# Create necessary directories in the image to ensure correct permissions
RUN mkdir -p ~/.claude ~/.config/gemini ~/.cloudcli ~/.forge ~/.ssh ~/.local/share/code-server

# Use dumb-init to handle signals correctly
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["/bin/bash", "-c", "cloudcli start"]
