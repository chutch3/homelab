# Kolibri - Offline Educational Platform

Kolibri is an open-source educational platform designed to provide access to high-quality educational content in low-resource environments. It works offline and provides access to Khan Academy, CK-12, and other educational libraries.

## Overview

This deployment provides:
- Offline access to educational content (Khan Academy, CK-12, educational videos)
- User management and progress tracking
- Classroom and coach features
- Content channel management
- Automatic SSL via Traefik
- Integration with Homepage dashboard
- Optimized storage architecture (iSCSI + CIFS)

## Storage Architecture

This stack uses a hybrid storage approach for optimal performance:

### iSCSI Storage (High Performance)
- **Location:** `/mnt/iscsi/app-data/kolibri`
- **Purpose:** Application data, SQLite database, user data, settings
- **Why:** SQLite databases require low-latency storage for optimal performance
- **Contents:**
  - SQLite database files
  - User progress and session data
  - Application configuration
  - Cache and temporary files

### CIFS Storage (High Capacity)
- **Location:** `//${NAS_SERVER}/kolibri_content`
- **Purpose:** Educational content (videos, exercises, documents)
- **Why:** Content files are large (10-100GB+ per channel) but don't require low latency
- **Contents:**
  - Educational video files
  - Practice exercises and assessments
  - HTML5 apps and interactive content
  - Images and documents

This architecture ensures:
- Fast database operations (iSCSI)
- Efficient content delivery (CIFS)
- Easy content management via NAS
- Optimal storage utilization

## Prerequisites

1. **iSCSI mount available** at `/mnt/iscsi/app-data/kolibri`
2. **CIFS/SMB share** named `kolibri_content` on your NAS
3. **Authentik OIDC provider** configured (optional, for SSO)
4. **Environment variables** configured in root `.env` file
5. **Storage requirements:**
   - iSCSI: 5-10 GB (application data)
   - CIFS: 20-200 GB (depending on content channels)

## Installation

### Step 1: Prepare Storage

#### Create iSCSI Directory

```bash
# On the host with iSCSI mount
mkdir -p /mnt/iscsi/app-data/kolibri
chmod 770 /mnt/iscsi/app-data/kolibri
```

#### Create CIFS Share on NAS

On your OpenMediaVault NAS or equivalent:

1. Create a new shared folder named `kolibri_content`
2. Configure SMB/CIFS share for the folder
3. Set appropriate permissions (read/write for service account)

**Example via OMV Web UI:**
- Navigate to: Storage → Shared Folders → Create
  - Name: `kolibri_content`
  - File system: Select your data filesystem
  - Path: `/kolibri_content`
  - Permissions: Users: read/write
- Navigate to: Services → SMB/CIFS → Shares → Create
  - Shared folder: `kolibri_content`
  - Public: No
  - Enable: Yes

**Example via SSH on NAS:**
```bash
# Create directory
mkdir -p /srv/dev-disk-by-uuid-xxxxx/kolibri_content
chmod 775 /srv/dev-disk-by-uuid-xxxxx/kolibri_content

# Add to SMB configuration
# Configure via OMV web interface or edit smb.conf
```

### Step 2: Configure Authentik OIDC Provider (Optional)

If you want SSO authentication via Authentik:

1. Log into Authentik at `https://auth.${BASE_DOMAIN}/`
2. Navigate to **Applications** → **Providers** → **Create**
3. Select **OAuth2/OpenID Provider**
4. Configure:
   - **Name:** Kolibri
   - **Authorization flow:** default-provider-authorization-implicit-consent
   - **Client type:** Confidential
   - **Redirect URIs:** `https://kolibri.${BASE_DOMAIN}/oidccallback/`
   - **Signing Key:** Select your certificate
5. Save and note the **Client ID** and **Client Secret**
6. Navigate to **Applications** → **Applications** → **Create**
7. Configure:
   - **Name:** Kolibri
   - **Slug:** kolibri
   - **Provider:** Select the Kolibri provider created above
8. Save the application

### Step 3: Configure Environment Variables

Add to your root `.env` file:

```bash
# Kolibri configuration
TZ=America/New_York                    # Optional: Timezone
PUID=1000                              # User ID for file permissions
PGID=1000                              # Group ID for file permissions

# SMB/CIFS credentials (required for content mount)
SMB_USERNAME=your_nas_username
SMB_PASSWORD=your_nas_password
SMB_DOMAIN=WORKGROUP
NAS_SERVER=nas.local                   # NAS IP/hostname for CIFS mount

# Authentik OIDC (optional, for SSO)
KOLIBRI_OAUTH_CLIENT_ID=your_client_id_from_authentik
KOLIBRI_OAUTH_CLIENT_SECRET=your_client_secret_from_authentik
```

### Step 4: Deploy Kolibri Service

```bash
# Deploy stack (automatically registers DNS and uptime monitoring for new stacks)
task ansible:deploy:stack -- -e "stack_name=kolibri"

# To skip DNS/uptime registration (if needed)
# task ansible:deploy:stack -- -e "stack_name=kolibri" -e "register_dns=false" -e "register_uptime=false"
```

**Note:** The deployment automatically:
- Detects if this is a new stack or update
- Registers DNS records only for new stacks
- Adds uptime monitoring only for new stacks
- Skips DNS/uptime for updates to existing stacks

### Step 5: OIDC Plugin

The OIDC plugin (`kolibri-oidc-client-plugin`) is installed automatically on every container start via the `install-oidc-plugin.sh` script. No manual action required.

### Step 6: Verify Deployment

```bash
# Check service status
docker stack ps kolibri

# View service logs
docker service logs kolibri_kolibri

# Test access
curl -I https://kolibri.${BASE_DOMAIN}/

# Check storage mounts
docker service inspect kolibri_kolibri --format '{{json .Spec.TaskTemplate.ContainerSpec.Mounts}}'
```

### Step 7: Initial Setup

1. Access Kolibri at `https://kolibri.${BASE_DOMAIN}/`

2. **If using Authentik OIDC:**
   - Click "Sign in with OpenID Connect" button
   - You'll be redirected to Authentik for authentication
   - After authentication, you'll be returned to Kolibri
   - First-time users will have accounts created automatically

3. **If NOT using Authentik:**
   - Complete the setup wizard:
     - Select your language
     - Choose facility type (e.g., "Formal school")
     - Create an admin account
     - Configure your facility name

4. Import content channels (see Content Management section below)

## Manual DNS/Uptime Configuration

If you need to manually configure DNS or uptime monitoring (e.g., after changes to docker-compose.yml):

```bash
# Configure DNS for Kolibri only
task ansible:configure:dns -- -e "stack_name=kolibri"

# Configure uptime monitoring for Kolibri only
task ansible:configure:uptime -- -e "stack_name=kolibri"

# Or configure for all services
task ansible:configure:dns
task ansible:configure:uptime
```

## Content Management

### Importing Educational Content

Kolibri content is organized into "channels" - collections of educational materials.

#### Via Web Interface

1. Navigate to `https://kolibri.${BASE_DOMAIN}/`
2. Log in as admin
3. Go to **Device** → **Channels**
4. Click **Import from Kolibri Studio**
5. Browse and select channels:
   - **Khan Academy (English):** Math, science, computing (~40 GB)
   - **CK-12:** STEM subjects, textbooks (~20 GB)
   - **African Storybook:** Children's literacy content (~2 GB)
   - **PhET Interactive Simulations:** Science simulations (~5 GB)
   - **MIT Blossoms:** Video lessons for math and science (~10 GB)

6. Select content to import (full channel or specific topics)
7. Wait for download to complete

#### Via Command Line

```bash
# List available channels
docker exec $(docker ps -q -f name=kolibri) kolibri manage listchannels network

# Import specific channel (example: Khan Academy)
docker exec $(docker ps -q -f name=kolibri) kolibri manage importchannel network <channel-id>

# Import content from channel
docker exec $(docker ps -q -f name=kolibri) kolibri manage importcontent network <channel-id>
```

### Popular Content Channels

| Channel | Size | Description |
|---------|------|-------------|
| Khan Academy (English) | 40+ GB | Math, science, computing, test prep |
| CK-12 | 20+ GB | Textbooks and STEM resources |
| African Storybook | 2 GB | Multilingual children's books |
| PhET Simulations | 5 GB | Interactive science simulations |
| MIT Blossoms | 10 GB | Math and science video lessons |
| GCF Learn Free | 3 GB | Technology and life skills |
| Sikana | 15 GB | How-to videos (health, arts, sports) |

### Managing Storage

Monitor content storage usage:

```bash
# Check CIFS storage usage (on NAS)
ssh admin@nas.local 'du -sh /path/to/kolibri_content'

# Check iSCSI storage usage (on host)
du -sh /mnt/iscsi/app-data/kolibri

# Check within container
docker exec $(docker ps -q -f name=kolibri) du -sh /kolibri_data
```

Delete unused channels via Web UI:
1. Go to **Device** → **Channels**
2. Click on channel to delete
3. Click **Options** → **Delete channel**

## User Management

### Creating Users

1. Navigate to **Facility** → **Users**
2. Click **New user**
3. Select user type:
   - **Learner:** Students
   - **Coach:** Teachers/facilitators
   - **Admin:** Full access

### Classroom Management

1. Navigate to **Facility** → **Classes**
2. Create classes and assign:
   - Coaches (teachers)
   - Learners (students)
3. Organize learners into groups within classes

### Progress Tracking

Coaches can track learner progress:
1. Navigate to **Coach** → **Class home**
2. View reports on:
   - Lesson progress
   - Exercise completion
   - Quiz scores
   - Time spent on content

## Configuration

### Kolibri Settings

Access via Web UI:
1. **Device** → **Settings**
   - Language settings
   - Content storage location (view only)
   - Allow guest access
   - Allow learner account creation

### Advanced Configuration

Environment variables (in docker-compose.yml):

```yaml
environment:
  - KOLIBRI_HOME=/kolibri_data              # Data directory
  - KOLIBRI_HTTP_PORT=8080                  # HTTP port
  - TZ=${TZ:-UTC}                           # Timezone
  - PUID=${PUID:-1000}                      # User ID
  - PGID=${PGID:-1000}                      # Group ID
```

## Usage

### For Administrators

1. **Import content:** Device → Channels
2. **Create users:** Facility → Users
3. **Set up classes:** Facility → Classes
4. **Monitor usage:** Device → Info
5. **Generate reports:** Coach → Reports

### For Coaches/Teachers

1. **Create lessons:** Coach → Plan → New lesson
2. **Assign quizzes:** Coach → Plan → New quiz
3. **Monitor progress:** Coach → Class home
4. **View reports:** Coach → Reports

### For Learners

1. Access assigned lessons at homepage
2. Complete exercises and quizzes
3. Track personal progress
4. Explore additional content in channels

## Troubleshooting

### Content Downloads Failing

**Issue:** Channel imports fail or hang

**Solutions:**

1. Check available storage on CIFS share:
   ```bash
   ssh admin@nas.local 'df -h /path/to/kolibri_content'
   ```

2. Verify CIFS mount is writable:
   ```bash
   docker exec $(docker ps -q -f name=kolibri) touch /kolibri_data/content/test
   ```

3. Check Kolibri logs:
   ```bash
   docker service logs kolibri_kolibri
   ```

4. Retry import via CLI:
   ```bash
   docker exec $(docker ps -q -f name=kolibri) kolibri manage importcontent network <channel-id>
   ```

### Database Performance Issues

**Issue:** Slow loading, timeouts

**Solutions:**

1. Verify iSCSI mount is working:
   ```bash
   mount | grep iscsi
   ```

2. Check database location:
   ```bash
   docker exec $(docker ps -q -f name=kolibri) ls -lh /kolibri_data/db.sqlite3
   ```

3. Optimize database:
   ```bash
   docker exec $(docker ps -q -f name=kolibri) kolibri manage vacuum
   ```

4. Check iSCSI latency:
   ```bash
   dd if=/dev/zero of=/mnt/iscsi/app-data/kolibri/test.dat bs=1M count=100 oflag=direct
   ```

### Service Won't Start

**Issue:** Container fails to start

**Solutions:**

1. Check volume mounts:
   ```bash
   docker service inspect kolibri_kolibri --format '{{json .Spec.TaskTemplate.ContainerSpec.Mounts}}'
   ```

2. Verify permissions:
   ```bash
   ls -ld /mnt/iscsi/app-data/kolibri
   ```

3. Check service logs:
   ```bash
   docker service logs kolibri_kolibri --tail 100
   ```

4. Verify SMB credentials in `.env` file

### Content Not Accessible

**Issue:** Learners see "Content unavailable"

**Solutions:**

1. Verify content is imported:
   - Device → Channels → Check channel status

2. Check content directory permissions:
   ```bash
   docker exec $(docker ps -q -f name=kolibri) ls -l /kolibri_data/content
   ```

3. Reimport problematic channel:
   - Device → Channels → Delete channel → Reimport

### OIDC/Authentik Authentication Issues

**Issue:** OIDC login not working or "Sign in with OpenID Connect" button missing

**Solutions:**

1. Verify OIDC plugin is installed and enabled:
   ```bash
   docker exec $(docker ps -q -f name=kolibri) kolibri plugin --list
   ```

   Should show `kolibri_oidc_client_plugin` as enabled.

2. If plugin not installed, install it:
   ```bash
   CONTAINER_ID=$(docker ps -q -f name=kolibri)
   docker cp stacks/apps/kolibri/install-oidc-plugin.sh $CONTAINER_ID:/tmp/
   docker exec $CONTAINER_ID /bin/bash /tmp/install-oidc-plugin.sh
   docker service update --force kolibri_kolibri
   ```

3. Check OIDC environment variables:
   ```bash
   docker service inspect kolibri_kolibri --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}'
   ```

   Verify all OIDC_* variables are set correctly.

4. Verify Authentik provider configuration:
   - Check redirect URI: `https://kolibri.${BASE_DOMAIN}/oidccallback/`
   - Verify client ID and secret match `.env` file
   - Ensure provider is assigned to Kolibri application

5. Check Kolibri logs for OIDC errors:
   ```bash
   docker service logs kolibri_kolibri | grep -i oidc
   ```

6. Test OIDC endpoints are accessible:
   ```bash
   curl -I https://auth.${BASE_DOMAIN}/application/o/authorize/
   curl -I https://auth.${BASE_DOMAIN}/application/o/token/
   ```

**Issue:** Users created via OIDC don't have proper permissions

**Solutions:**

1. Log in as admin (non-OIDC account)
2. Navigate to **Facility** → **Users**
3. Find the OIDC-created users
4. Assign appropriate roles (Learner, Coach, Admin)
5. Add to classes/groups as needed

## Backup and Restore

### Backup User Data and Progress

```bash
# Backup database and user data (from iSCSI)
tar -czf kolibri-backup-$(date +%Y%m%d).tar.gz -C /mnt/iscsi/app-data kolibri/

# Backup to NAS
scp kolibri-backup-*.tar.gz admin@nas.local:/srv/backups/
```

### Backup Content

Content on CIFS share can be backed up separately:

```bash
# On NAS
tar -czf kolibri-content-backup-$(date +%Y%m%d).tar.gz /path/to/kolibri_content/
```

### Restore

```bash
# Stop service
docker service scale kolibri_kolibri=0

# Restore data
tar -xzf kolibri-backup-YYYYMMDD.tar.gz -C /mnt/iscsi/app-data/

# Restore content (on NAS)
ssh admin@nas.local 'tar -xzf kolibri-content-backup-YYYYMMDD.tar.gz -C /'

# Start service
docker service scale kolibri_kolibri=1
```

## Maintenance

### Update Kolibri

```bash
# Pull latest image
docker pull learningequality/kolibri:latest

# Update service
docker service update --image learningequality/kolibri:latest kolibri_kolibri

# Or redeploy the stack (won't re-register DNS/uptime since it's an existing stack)
task ansible:deploy:stack -- -e "stack_name=kolibri"
```

### Remove Kolibri

To completely remove the Kolibri stack:

```bash
# Remove stack only (preserves volumes, DNS, and uptime)
task ansible:teardown:stack -- -e "stack_name=kolibri" -e "remove_volumes=false" -e "remove_dns=false" -e "remove_uptime=false"

# Remove stack and DNS/uptime (preserves volumes)
task ansible:teardown:stack -- -e "stack_name=kolibri"

# Remove everything including data volumes
task ansible:teardown:stack -- -e "stack_name=kolibri" -e "remove_volumes=true"
```

**Note:** By default, teardown removes:
- The Docker stack (always)
- DNS records (default: true)
- Uptime monitors (default: true)
- Volumes (default: false, must explicitly set to true)

### Update Content Channels

1. Navigate to **Device** → **Channels**
2. Look for channels with "Update available"
3. Click **Options** → **Manage**
4. Select **Update** to download latest version

## Architecture

**Components:**
- **Kolibri Server (Docker):** Educational platform application
- **iSCSI Storage:** Low-latency storage for SQLite database
- **CIFS Storage:** High-capacity storage for content
- **Traefik:** SSL termination and reverse proxy

**Data Flow:**
1. User accesses `https://kolibri.${BASE_DOMAIN}/`
2. Traefik routes to Kolibri container on port 8080
3. Kolibri reads/writes database from iSCSI mount (`/kolibri_data`)
4. Kolibri serves content from CIFS mount (`/kolibri_data/content`)
5. Content downloads stored directly to CIFS share

**Storage Benefits:**
- **iSCSI for database:** Ensures fast queries and transactions
- **CIFS for content:** Allows easy management via NAS, large capacity
- **Separation:** Database performance not affected by large content files
- **Scalability:** Add content without impacting application performance

## Resources

- **Kolibri Official Site:** https://learningequality.org/kolibri/
- **Kolibri Documentation:** https://kolibri.readthedocs.io/
- **Content Library:** https://studio.learningequality.org/
- **Kolibri Docker Hub:** https://hub.docker.com/r/learningequality/kolibri
- **Community Forum:** https://community.learningequality.org/

## Common Use Cases

### Home Education
- Import Khan Academy and CK-12
- Create family accounts
- Track children's progress
- Offline learning during travel

### Community Center/Library
- Set up public learning kiosks
- Provide free educational access
- Track community engagement
- Offer courses and workshops

### Emergency Preparedness
- Offline educational content
- Medical and safety information
- Skill-building resources
- Network-independent operation

## License

- **Kolibri:** MIT License
- **Content:** Varies by channel (Khan Academy: CC BY-NC-SA, CK-12: CC BY-SA, etc.)
