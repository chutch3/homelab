#!/usr/bin/env bash
# Bootstrap this machine to work with the homelab repo.
# Usage: bash setup.sh
set -euo pipefail

if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; RESET=''
fi

ok()     { echo -e "${GREEN}  ✔${RESET}  $*"; }
skip()   { echo -e "${BLUE}  –${RESET}  $*"; }
info()   { echo -e "${YELLOW}  →${RESET}  $*"; }
fail()   { echo -e "${RED}  ✘${RESET}  $*" >&2; }
header() { echo -e "\n${BOLD}${BLUE}══ $* ══${RESET}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
have() { command -v "$1" &>/dev/null; }

# shellcheck disable=SC1091
[[ -f /etc/os-release ]] && source /etc/os-release
if [[ "${ID:-}" != "ubuntu" && "${ID_LIKE:-}" != *"debian"* ]]; then
    echo -e "${YELLOW}Warning:${RESET} This script targets Ubuntu/Debian; ${PRETTY_NAME:-your OS} may need manual adjustments."
    echo ""
fi

export PATH="$HOME/.local/bin:$PATH"

load_fnm_env() {
    local env_output
    if ! env_output="$(fnm env --shell bash 2>&1)"; then
        fail "fnm env setup failed: $env_output"
        return 1
    fi
    eval "$env_output"
}

# fnm and its managed tools (node, npm, bw) are not on PATH in a bare subshell.
# Find and load fnm if it's already installed so re-runs detect everything correctly.
bootstrap_fnm() {
    have fnm && return 0

    local fnm_dir="${FNM_DIR:-}"
    for candidate in "$fnm_dir" "$HOME/.local/share/fnm" "$HOME/.fnm"; do
        if [[ -n "$candidate" && -f "$candidate/fnm" ]]; then
            export PATH="$candidate:$PATH"
            break
        fi
    done

    have fnm && eval "$(fnm env --shell bash 2>/dev/null)" || true
}

bootstrap_fnm

# ── 1. uv ─────────────────────────────────────────────────────────────────────
header "uv"

if have uv; then
    skip "uv $(uv --version) already installed"
else
    info "Installing uv..."
    curl -fsSL https://astral.sh/uv/install.sh | sh \
        || { fail "uv installation failed"; exit 1; }
    export PATH="$HOME/.local/bin:$PATH"
    ok "uv installed"
fi

# ── 2. Task ───────────────────────────────────────────────────────────────────
header "Task runner"

if have task; then
    skip "task $(task --version) already installed"
else
    info "Installing task to ~/.local/bin..."
    mkdir -p "$HOME/.local/bin"
    curl -fsSL https://taskfile.dev/install.sh \
        | sh -s -- -d -b "$HOME/.local/bin" \
        || { fail "task installation failed"; exit 1; }
    ok "task installed"
    echo '  Add to ~/.bashrc or ~/.zshrc if needed: export PATH="$HOME/.local/bin:$PATH"'
fi

# ── 3. Node.js ────────────────────────────────────────────────────────────────
header "Node.js"

NODE_AVAILABLE=false
BW_SKIP_REASON=""

ensure_node() {
    if have node && have npm; then
        skip "node $(node --version) / npm $(npm --version) already installed"
        NODE_AVAILABLE=true
        return 0
    fi

    if have fnm; then
        load_fnm_env
        if ! have node; then
            info "fnm found but no active Node version — installing LTS..."
            fnm install --lts || { fail "fnm: LTS install failed"; return 1; }
            fnm use lts-latest
            load_fnm_env
        fi
        skip "node $(node --version) loaded via fnm"
        NODE_AVAILABLE=true
        return 0
    fi

    echo ""
    echo -e "  Node.js is required for the Bitwarden CLI but is not installed."

    if [[ ! -t 0 ]]; then
        BW_SKIP_REASON="Node.js not installed (non-interactive — re-run manually to install)"
        return 0
    fi

    read -r -p "  Install Node.js via fnm? [Y/n] " reply
    reply="${reply:-Y}"
    if [[ ! "$reply" =~ ^[Yy] ]]; then
        BW_SKIP_REASON="Node.js not installed (skipped by user)"
        return 0
    fi

    info "Installing fnm..."
    curl -fsSL https://fnm.vercel.app/install | bash \
        || { fail "fnm installation failed"; return 1; }

    # Honour $FNM_DIR, then fall back to the two common install locations
    local fnm_dir="${FNM_DIR:-}"
    [[ -z "$fnm_dir" || ! -f "$fnm_dir/fnm" ]] && fnm_dir="$HOME/.local/share/fnm"
    [[ ! -f "$fnm_dir/fnm" ]]                   && fnm_dir="$HOME/.fnm"
    if [[ ! -f "$fnm_dir/fnm" ]]; then
        fail "fnm binary not found after install (checked ~/.local/share/fnm and ~/.fnm)"
        fail "Open a new terminal, run: fnm install --lts && fnm use lts-latest, then re-run setup.sh"
        return 1
    fi

    export PATH="$fnm_dir:$PATH"
    load_fnm_env

    info "Installing Node.js LTS..."
    fnm install --lts || { fail "Node.js LTS installation failed"; return 1; }
    fnm use lts-latest
    load_fnm_env

    ok "Node $(node --version) installed via fnm"
    echo "  fnm configured in your shell profile — open a new terminal to use it globally."
    NODE_AVAILABLE=true
}

ensure_node

# ── 4. Bitwarden CLI ──────────────────────────────────────────────────────────
header "Bitwarden CLI"

if have bw; then
    skip "bw $(bw --version) already installed"
elif [[ -n "$BW_SKIP_REASON" ]]; then
    skip "bw — $BW_SKIP_REASON"
elif [[ "$NODE_AVAILABLE" == false ]]; then
    skip "bw — Node.js not available"
else
    NPM_PREFIX="$(npm config get prefix)"
    if [[ "$NPM_PREFIX" == /usr* ]]; then
        # System npm (installed via apt) puts globals under /usr, which needs sudo
        info "System npm detected — installing Bitwarden CLI with sudo..."
        sudo npm install -g @bitwarden/cli --quiet \
            || { fail "Bitwarden CLI installation failed"; exit 1; }
    else
        info "Installing Bitwarden CLI via npm..."
        npm install -g @bitwarden/cli --quiet \
            || { fail "Bitwarden CLI installation failed"; exit 1; }
    fi
    export PATH="$NPM_PREFIX/bin:$PATH"
    ok "bw installed"
fi

# ── 5. Python dependencies ────────────────────────────────────────────────────
header "Python dependencies"

cd "$SCRIPT_DIR"
uv sync || { fail "uv sync failed"; exit 1; }
ok "Dependencies installed (.venv)"

# ── 6. Pre-commit hooks ───────────────────────────────────────────────────────
header "Pre-commit hooks"

if [[ -d .git ]]; then
    uv run pre-commit install || { fail "pre-commit install failed"; exit 1; }
    ok "pre-commit hooks installed"
else
    skip "not a git repo — skipping pre-commit install"
fi

# ── 7. Ansible Galaxy collections ────────────────────────────────────────────
header "Ansible Galaxy collections"

uv run ansible-galaxy collection install \
    -r ansible/requirements.yml \
    -p ansible/collections \
    --timeout 60 \
    || { fail "Ansible Galaxy install failed"; exit 1; }
ok "Ansible collections installed"

# ── 8. Config files ───────────────────────────────────────────────────────────
header "Config files"

copy_example() {
    local src="$1" dst="$2"
    if [[ -f "$dst" ]]; then
        skip "$dst already exists"
    elif [[ -f "$src" ]]; then
        cp "$src" "$dst"
        ok "Created $dst (edit before use)"
    fi
}

copy_example .env.example .env
copy_example ansible/inventory/group_vars/all/ssh.yml.example \
             ansible/inventory/group_vars/all/ssh.yml
copy_example ansible/inventory/group_vars/all/snmp.yml.example \
             ansible/inventory/group_vars/all/snmp.yml

# ── 9. Summary ────────────────────────────────────────────────────────────────
header "Done"

echo ""
echo -e "${BOLD}Tools:${RESET}"
for bin in task uv node bw docker; do
    if have "$bin"; then
        echo -e "  ${GREEN}✔${RESET}  $bin"
    elif [[ "$bin" == "bw" && -n "$BW_SKIP_REASON" ]]; then
        echo -e "  ${YELLOW}–${RESET}  bw  ($BW_SKIP_REASON)"
    else
        echo -e "  ${YELLOW}!${RESET}  $bin  (not in current shell — open a new terminal and re-check)"
    fi
done

echo ""
echo -e "${BOLD}Next steps:${RESET}"
echo "  1. Edit .env — set BASE_DOMAIN, CF_Token, and passwords"
echo "  2. Create ansible/inventory/02-hosts.yml with your node IPs"
echo "     (see ansible/inventory/01-structure.yml for format)"
echo "  3. task ansible:ssh:generate    — create the homelab SSH key"
echo "  4. task ansible:ssh:distribute  — push the key to your nodes"
echo "  5. task ansible:bootstrap       — install Docker on all nodes"
echo "  6. task ansible:cluster:init    — initialize Docker Swarm"
echo "  7. task ansible:deploy          — deploy all services"
echo ""
echo -e "  ${BLUE}To restore secrets from Bitwarden:${RESET} task ansible:secrets:login && task secrets:pull"
echo -e "  ${BLUE}To run tests locally:${RESET}             sudo apt install bats && task test-fast"
echo -e "  ${BLUE}All commands:${RESET}                     task --list"
echo ""
