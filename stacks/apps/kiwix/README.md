# Kiwix - Offline Knowledge Archive

Kiwix enables you to have offline access to Wikipedia, Stack Exchange, medical guides, and other educational content. Perfect for network-independent knowledge access and emergency preparedness.

## Overview

This deployment provides:
- Offline Wikipedia, WikiMed, Stack Overflow, and more
- Automatic monthly update checks with email notifications
- Read-only CIFS mount for security and performance
- Full-text search across all content
- Automatic SSL via Traefik
- Integration with Homepage dashboard

## Storage Requirements

**Starter Pack (~330GB):**
- English Wikipedia (no pictures): 50 GB
- Project Gutenberg (60,000+ public domain books): 206 GB
- WikiMed (medical encyclopedia): 10 GB
- Stack Overflow (programming Q/A): 50 GB
- FreeCodeCamp (coding tutorials): 5 GB
- OpenStreetMap Wiki (mapping/navigation): 0.3 GB
- Gardening Stack Exchange (growing food): 0.8 GB
- DIY Stack Exchange (repairs/building): 1.8 GB
- Cooking Stack Exchange (food prep): 0.2 GB
- Sustainability Stack Exchange (self-sufficiency): 0.02 GB
- Wikivoyage (travel guides): 5 GB

**Full Deployment (~770GB):**
- English Wikipedia (with images): 119 GB
- All Stack Exchange sites: ~200 GB
- Multiple language Wikipedias: ~300 GB
- Educational content: ~100 GB
- Project Gutenberg: ~50 GB

## Prerequisites

1. **OpenMediaVault NAS** (or any Linux system accessible via SSH)
2. **Available Storage:** 500GB - 2TB on NAS
3. **NAS Configuration:** NAS defined in `machines.yaml` with role `storage`
4. **SSH Access:** SSH key authentication to NAS
5. **Email System:** Mail command configured on NAS for notifications (optional)
6. **Environment Variables:** SMB credentials configured in root `.env` file

## Installation

### Step 1: NAS Setup

Run the interactive setup script to configure your NAS:

```bash
cd stacks/apps/kiwix
./setup-nas-downloads.sh
```

This script will:
1. Prompt for NAS connection details (hostname, SSH user, SSH key path)
2. Test SSH connectivity
3. Prompt for storage paths on NAS
4. Prompt for email address for notifications
5. Create required directories on NAS
6. Copy `zim-manager.sh` to `/usr/local/bin/` on NAS
7. Create configuration file at `/etc/kiwix-config.sh` on NAS
8. Set up monthly cron job for update checks
9. Test email notifications
10. Optionally start initial download of starter pack

The script automatically discovers your NAS from `machines.yaml` (looks for machine with key "nas"). If not found in machines.yaml, it will prompt for connection details.

**Example machines.yaml entry:**
```yaml
machines:
  nas:
    ip: 192.168.86.189
    role: storage
    ssh_user: cody
    swarm_node: false
```

**Example prompts (if needed):**
```
ZIM data directory on NAS [/srv/kiwix_data]:
Log directory on NAS [/var/log/kiwix]:
Email address for notifications [admin@example.com]: you@example.com
Run initial download of starter pack now? (y/N): y
```

### Step 2: Monitor Download Progress

If you started the initial download, monitor it:

```bash
# Check download progress
ssh admin@nas.local 'tail -f /var/log/kiwix/init.log'

# Check storage usage
ssh admin@nas.local 'du -sh /srv/kiwix_data'

# List downloaded files
ssh admin@nas.local 'ls -lh /srv/kiwix_data/*.zim'
```

**Note:** Initial downloads can take several hours for 100GB+ of data depending on your NAS's internet connection speed.

### Step 3: Deploy Kiwix Service

Once at least one ZIM file has been downloaded, deploy the Kiwix Docker service:

```bash
cd /path/to/selfhosted.sh
./selfhosted.sh deploy --skip-infra --only-apps kiwix
```

### Step 4: Verify Deployment

```bash
# Check service status
docker stack ps kiwix

# View service logs
docker service logs kiwix_kiwix

# Test access
curl -I https://kiwix.${BASE_DOMAIN}/

# Access via browser
open https://kiwix.${BASE_DOMAIN}/
```

You should see the Kiwix library with all downloaded ZIM files listed.

## Configuration

### Environment Variables

Add to root `.env` file:

```bash
# Kiwix configuration
TZ=America/New_York                    # Optional: Timezone for service

# SMB/CIFS credentials (required for NAS mount)
SMB_USERNAME=your_nas_username
SMB_PASSWORD=your_nas_password
SMB_DOMAIN=WORKGROUP
NAS_SERVER=192.168.86.189              # Must match NAS IP from machines.yaml

# SSH configuration (optional - setup script uses machines.yaml)
SSH_KEY_FILE=~/.ssh/selfhosted_rsa
```

**Important:**
- The setup scripts automatically discover NAS connection info from `machines.yaml`
- `NAS_SERVER` in `.env` must match the IP in `machines.yaml` (used by docker-compose for CIFS mount)
- SSH user is discovered from `machines.yaml`, no need to configure in `.env`

### Update Schedule

The NAS cron job runs automatically on the 1st of each month at 2 AM:

```cron
0 2 1 * * . /etc/kiwix-config.sh && /usr/local/bin/zim-manager.sh check
```

This generates a report and emails it to your configured address. Updates must be manually approved and downloaded.

## Usage

### Accessing Content

1. Navigate to `https://kiwix.${BASE_DOMAIN}/`
2. Browse the library of available ZIM files
3. Click any archive to access its content
4. Use the search feature to find articles across all archives

### Manual ZIM Management

#### Download a Specific ZIM File

```bash
ssh admin@nas.local 'zim-manager.sh download https://download.kiwix.org/zim/wikipedia/wikipedia_es_all_nopic_2025-11.zim'
```

#### Run Update Check Manually

```bash
ssh admin@nas.local 'zim-manager.sh check'
```

#### Re-run Initial Setup

```bash
ssh admin@nas.local 'zim-manager.sh init'
```

#### View Logs

```bash
ssh admin@nas.local 'ls -l /var/log/kiwix/'
ssh admin@nas.local 'cat /var/log/kiwix/zim-manager-*.log'
```

### Finding ZIM Files

Browse available ZIM files at: https://download.kiwix.org/zim/

**Prepper/Emergency Content:**
- **OpenStreetMap Wiki:** `https://download.kiwix.org/zim/other/openstreetmap-wiki_en_all_nopic_2025-07.zim` (317 MB)
- **Gardening Stack Exchange:** `https://download.kiwix.org/zim/stack_exchange/gardening.stackexchange.com_en_all_2025-10.zim` (839 MB)
- **DIY Stack Exchange:** `https://download.kiwix.org/zim/stack_exchange/diy.stackexchange.com_en_all_2025-08.zim` (1.8 GB)
- **Cooking Stack Exchange:** `https://download.kiwix.org/zim/stack_exchange/cooking.stackexchange.com_en_all_2025-07.zim` (202 MB)
- **Sustainability Stack Exchange:** `https://download.kiwix.org/zim/stack_exchange/sustainability.stackexchange.com_en_all_2025-10.zim` (24 MB)
- **Project Gutenberg (English):** `https://download.kiwix.org/zim/gutenberg/gutenberg_en_all_2025-11.zim` (206 GB - 60,000+ books readable in browser)

**Popular Archives:**
- **Wikipedia (all languages):** `https://download.kiwix.org/zim/wikipedia/`
- **Stack Exchange (all sites):** `https://download.kiwix.org/zim/stack_exchange/`
- **WikiMed (medical):** `https://download.kiwix.org/zim/other/wikimed_en_all_YYYY-MM.zim`
- **Wikivoyage (travel):** `https://download.kiwix.org/zim/wikivoyage/`
- **Project Gutenberg (books):** `https://download.kiwix.org/zim/gutenberg/`

## Troubleshooting

### Service Can't Access ZIM Files

**Issue:** Kiwix shows empty library or "No content available"

**Solutions:**
1. Verify ZIM files exist on NAS:
   ```bash
   ssh admin@nas.local 'ls -lh /srv/kiwix_data/*.zim'
   ```

2. Check CIFS mount in Docker:
   ```bash
   docker service inspect kiwix_kiwix --format '{{json .Spec.TaskTemplate.ContainerSpec.Mounts}}'
   ```

3. Verify SMB credentials in `.env` file

4. Check service logs:
   ```bash
   docker service logs kiwix_kiwix
   ```

### Downloads Failing on NAS

**Issue:** `zim-manager.sh` downloads fail

**Solutions:**
1. Check internet connectivity on NAS:
   ```bash
   ssh admin@nas.local 'ping -c 4 download.kiwix.org'
   ```

2. Verify wget is installed:
   ```bash
   ssh admin@nas.local 'which wget'
   ```

3. Check available storage:
   ```bash
   ssh admin@nas.local 'df -h /srv/kiwix_data'
   ```

4. Review download logs:
   ```bash
   ssh admin@nas.local 'tail -100 /var/log/kiwix/init.log'
   ```

### Email Notifications Not Working

**Issue:** Monthly update reports not being emailed

**Solutions:**
1. Test mail command on NAS:
   ```bash
   ssh admin@nas.local 'echo "Test" | mail -s "Test" your@email.com'
   ```

2. Configure mail on OpenMediaVault:
   - Navigate to: System → Notification → Settings
   - Configure SMTP server, port, authentication
   - Test email notification

3. Check cron job is configured:
   ```bash
   ssh admin@nas.local 'crontab -l | grep zim-manager'
   ```

### Service Restart Required After Adding ZIM Files

This is expected behavior. The Kiwix service mounts the data directory as read-only. After adding new ZIM files:

```bash
docker service update --force kiwix_kiwix
```

## Maintenance

### Updating zim-manager.sh Script

When the zim-manager.sh script is updated (e.g., new ZIM files added to STARTER_PACK), update it on your NAS:

```bash
cd stacks/apps/kiwix
./setup-nas-downloads.sh update
```

This will:
1. Backup the existing script on NAS
2. Copy the new version from your local repo
3. Make it executable
4. Verify the installation

The script automatically discovers your NAS from machines.yaml and uses SSH_KEY_FILE from your .env file.

### Updating ZIM Files

When monthly update check notifies you of new versions:

1. Review the email report
2. Download updated ZIM files:
   ```bash
   ssh admin@nas.local 'zim-manager.sh download <url>'
   ```
3. Delete old versions:
   ```bash
   ssh admin@nas.local 'rm /srv/kiwix_data/old-file.zim'
   ```
4. Restart Kiwix service:
   ```bash
   docker service update --force kiwix_kiwix
   ```

### Storage Management

Monitor storage usage:

```bash
# Overall usage
ssh admin@nas.local 'du -sh /srv/kiwix_data'

# Per-file breakdown
ssh admin@nas.local 'du -h /srv/kiwix_data/*.zim | sort -hr'
```

## Architecture

**Components:**
- **Kiwix Server (Docker):** Serves ZIM files via web interface
- **ZIM Manager (NAS):** Downloads and manages ZIM files on OpenMediaVault NAS
- **Cron (NAS):** Monthly update checks (uses OMV's RPC API with sentinel UUID for idempotent cron job creation)
- **CIFS Volume:** Read-only network mount for ZIM files

**Data Flow:**
1. NAS downloads ZIM files directly from download.kiwix.org
2. Files stored in `/srv/kiwix_data` on NAS
3. Docker service mounts via CIFS (read-only)
4. Kiwix serves content on port 8080
5. Traefik provides SSL and routing at `kiwix.${BASE_DOMAIN}`

**Benefits:**
- No intermediate storage needed (saves 100GB+)
- Downloads leverage NAS's network and storage
- Read-only mount improves security
- Simpler architecture than Docker sidecar approach

## Scripts Reference

### setup-nas-downloads.sh

Setup and management script for Kiwix NAS configuration.

**Commands:**
```bash
# Initial setup (interactive)
./setup-nas-downloads.sh setup
./setup-nas-downloads.sh          # Default command

# Update zim-manager.sh on NAS
./setup-nas-downloads.sh update

# Show help
./setup-nas-downloads.sh --help
```

**What it does:**
- Discovers NAS from `machines.yaml` automatically
- Sets up directories and configuration on NAS
- Copies zim-manager.sh script to NAS
- Configures cron job for monthly updates
- Tests email notifications

### zim-manager.sh (runs on NAS)

ZIM file download and management script (runs on the NAS itself).

**Commands:**
```bash
# Download starter pack (330GB)
ssh root@nas 'zim-manager.sh init'

# Check for available updates (sends email report)
ssh root@nas 'zim-manager.sh check'

# Download specific ZIM file
ssh root@nas 'zim-manager.sh download <url>'
```

**Examples:**
```bash
# Download Project Gutenberg
ssh root@nas 'zim-manager.sh download https://download.kiwix.org/zim/gutenberg/gutenberg_en_all_2025-11.zim'

# Download Spanish Wikipedia
ssh root@nas 'zim-manager.sh download https://download.kiwix.org/zim/wikipedia/wikipedia_es_all_nopic_2025-11.zim'
```

## Resources

- **Kiwix Official Site:** https://www.kiwix.org/
- **ZIM File Library:** https://download.kiwix.org/zim/
- **Kiwix Server Documentation:** https://github.com/kiwix/kiwix-tools
- **OpenMediaVault:** https://www.openmediavault.org/
- **Wikipedia ZIM Files:** https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/

## Future Enhancements

Planned improvements:
- Automatic download of new versions (with manual approval)
- Web UI for ZIM management
- Integration with Ollama for RAG (Retrieval-Augmented Generation)
- Custom search API wrapper
- Cross-archive search with Meilisearch

## License

This deployment uses:
- **Kiwix:** GPL-3.0
- **ZIM Content:** Varies by archive (Wikipedia: CC BY-SA, Stack Overflow: CC BY-SA, etc.)
