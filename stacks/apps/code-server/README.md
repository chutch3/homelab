# Web Dev Environment (code-server & ClaudeCodeUI)

This deployment provides a complete, browser-based development environment backed by your homelab's OCFS2 cluster storage. It includes both a fully-featured VS Code instance (`code-server`) and a unified AI agent CLI (`ClaudeCodeUI`).

## Overview

This deployment provides:
- **code-server:** A fully functional VS Code instance accessible from any browser.
- **ClaudeCodeUI:** A web dashboard for running CLI agents like Claude Code and Gemini-CLI.
- **Shared Workspace:** Both tools mount the exact same workspace directory, so code edited in the IDE is immediately available to the AI agents.
- **Unified SSH Identity:** A shared SSH key volume ensures both the IDE and the AI agents can seamlessly clone private GitHub repositories and SSH into homelab nodes without password prompts.
- **Persistent AI Configs:** API keys and chat histories for Claude and Gemini are saved to persistent cluster storage.

## Storage Architecture

This stack relies entirely on the **iSCSI + OCFS2 Cluster Filesystem** to ensure the development environment is instantly available and perfectly synced across any node in the Docker Swarm.

**Base Location:** `/mnt/iscsi/app-data/dev-env`

- **`workspace/`**: The actual directory where your code, projects, and repositories live.
- **`code-server/config/`**: IDE settings, extensions, and user preferences.
- **`shared-ssh/`**: The `.ssh` directory containing your keys and config.
- **`ai-configs/`**: Contains `.claude` and `.config/gemini` to persist API keys and sessions.

## Prerequisites

1. **iSCSI mount available** at `/mnt/iscsi/app-data/` on your cluster nodes.
2. A valid **homelab SSH key** (`~/.ssh/homelab_rsa`) on the machine where you run the setup script.
3. (Optional) Set `CODE_SERVER_PASSWORD="your-secure-password"` in your root `.env` file. If not set, the default is `secretpassword`.

## Installation & Setup

### Step 1: Run the Setup Script
Before deploying the stacks, you **must** run the setup script. This script creates the necessary OCFS2 directories, sets the correct `1000:1000` ownership, copies your homelab SSH key, and generates an SSH config file.

```bash
# Run this from any node in the cluster
sudo ./stacks/apps/code-server/setup.sh
```

### Step 2: Deploy the Stacks

You can deploy the tools together or individually using the homelab's standard Ansible pipeline:

```bash
# Deploy code-server (Web IDE)
task ansible:deploy:service -- -e "stack_name=code-server"

# Deploy ClaudeCodeUI (AI Agents)
task ansible:deploy:service -- -e "stack_name=claudecodeui"
```

The Ansible playbook will automatically handle registering the Traefik routes (`https://code.${BASE_DOMAIN}` and `https://ai.${BASE_DOMAIN}`) and Homepage dashboard entries.

## Post-Deployment: GitHub Setup

Your dev environment is already configured to securely access your internal homelab nodes using the `homelab_rsa` key. To clone private repositories from GitHub, you need to generate a new key:

1. Open `https://code.${BASE_DOMAIN}` in your browser.
2. Open the integrated terminal (`Ctrl` + `` ` ``).
3. Run the following command to generate a new key specifically for GitHub:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
   *(Press **Enter** when prompted to accept the default file path: `/config/.ssh/id_ed25519`)*
4. View the generated public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
5. Copy the output and add it to your GitHub account (Settings -> SSH and GPG keys -> New SSH key).

Because the `.ssh` directory is shared, **ClaudeCodeUI will instantly inherit this GitHub key** and can autonomously clone or push to your private repositories.

## Managing AI API Keys

### Claude Code
1. Open `https://ai.${BASE_DOMAIN}`.
2. In the terminal tab, run:
   ```bash
   claude login
   ```
3. Follow the OAuth flow to authenticate your Anthropic account. Your session token is saved to the persistent OCFS2 volume.

### Gemini-CLI
1. Obtain an API key from Google AI Studio.
2. In the `ai.${BASE_DOMAIN}` terminal, run:
   ```bash
   gemini setup
   ```
3. Paste your API key when prompted. This is saved to the persistent OCFS2 volume.

## Troubleshooting

### Permission Errors / Cannot edit files
If you encounter permission denied errors when creating files in the IDE or running AI agents, the OCFS2 permissions might be misaligned. Run the setup script again, or manually fix it:
```bash
sudo chown -R 1000:1000 /mnt/iscsi/app-data/dev-env
```

### SSH Prompts for Password
If SSHing into a homelab node asks for a password, verify that the `homelab_rsa` key was successfully copied during setup:
```bash
ls -la /mnt/iscsi/app-data/dev-env/shared-ssh/
```
If it is missing, manually copy your private key into that directory and name it `homelab_rsa`, ensuring the permissions are `600`.

### AI Agents Can't Clone GitHub Repos
Ensure you generated an `id_ed25519` key (or `id_rsa`) inside the code-server terminal, and that the public key is attached to your GitHub account. Do not overwrite the `homelab_rsa` key, as that is reserved for internal network access.
