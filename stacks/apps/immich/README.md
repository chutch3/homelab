# Immich - Photo and Video Management

Immich is a high-performance, self-hosted photo and video management solution with mobile apps, automatic backup, facial recognition, and machine learning capabilities.

## Overview

This deployment provides:
- Modern web and mobile interfaces (iOS & Android apps)
- Automatic photo/video backup from mobile devices
- AI-powered facial recognition and object detection
- Smart search using machine learning
- External library support for existing photo collections
- Timeline view, albums, and sharing
- Live photos, RAW support, and video transcoding
- Automatic SSL via Traefik
- Integration with Homepage dashboard

## Coexistence with PhotoPrism

This stack is designed to coexist peacefully with PhotoPrism, allowing you to:
- Run both applications simultaneously for evaluation
- Share access to existing photo library (read-only)
- Maintain separate upload directories
- Choose your preferred solution without data migration

**Key Differences:**

| Feature | PhotoPrism | Immich |
|---------|-----------|--------|
| Domain | `photo.${BASE_DOMAIN}` | `photos.${BASE_DOMAIN}` |
| Upload Storage | `photoprism_storage` | `immich_upload` |
| Shared Library | `all_data` (read/write) | `all_data` (read-only) |
| Database | MariaDB (`photoprism_database`) | PostgreSQL (`immich_pgdata`) |
| Mobile Apps | Web only | iOS & Android native apps |
| ML Features | TensorFlow GPU | PyTorch CPU/GPU |

## Storage Architecture

### Immich Upload Library
```yaml
immich_upload:
  device: "//${NAS_SERVER}/immich_upload"
```
- **New uploads via Immich** are stored here
- Immich manages folder structure automatically
- Independent from PhotoPrism

### Shared Photo Library (Read-Only)
```yaml
all_data:
  device: "//${NAS_SERVER}/all_data"
  options: "ro"  # Read-only mount
```
- **Your existing PhotoPrism library**
- Mounted at `/mnt/media/photos` in Immich
- Read-only to prevent accidental modifications
- Configure as External Library in Immich UI

## Prerequisites

1. **Storage:** NAS share `/immich_upload` created
2. **Existing Library:** Optional `/all_data` share (for PhotoPrism photos)
3. **Environment Variables:** Database credentials in `.env`
4. **Resources:** 4GB+ RAM recommended for ML features

## Installation

### Step 1: Create NAS Share

Create the upload directory on your NAS:

```bash
# SSH to your NAS and create the directory
ssh admin@nas.local 'mkdir -p /srv/immich_upload'
```

### Step 2: Configure Environment Variables

Verify these are set in your root `.env` file (already added by setup):

```bash
# Immich database credentials
IMMICH_DB_PASSWORD=your_secure_password
IMMICH_DB_USERNAME=postgres
IMMICH_DB_DATABASE_NAME=immich
IMMICH_VERSION=release

# Storage credentials (shared with other services)
SMB_USERNAME=your_nas_username
SMB_PASSWORD=your_nas_password
SMB_DOMAIN=WORKGROUP
NAS_SERVER=nas.your-domain.com
```

### Step 3: Deploy Immich

```bash
# Deploy only Immich
./homelab deploy --only-apps immich

# Or deploy with infrastructure
./homelab deploy
```

### Step 4: Initial Setup

1. Navigate to `https://photos.${BASE_DOMAIN}`
2. Create admin account (first user becomes admin)
3. Configure settings (optional):
   - Enable machine learning features
   - Configure video transcoding
   - Set up user accounts

### Step 5: Configure External Library (Optional)

To access your existing PhotoPrism photos:

1. Go to **Administration** → **External Libraries**
2. Click **Create External Library**
3. Configure:
   - **Name:** PhotoPrism Library
   - **Import Path:** `/mnt/media/photos`
   - **Scan Schedule:** Manual or Automatic
   - **Exclusion Patterns:** (optional) `**/Raw/**` to skip RAW files
4. Click **Scan Library**

The existing photos will appear in your timeline alongside new Immich uploads.

## Mobile Apps

Download the official Immich mobile apps:
- **iOS:** [App Store](https://apps.apple.com/us/app/immich/id1613945652)
- **Android:** [Google Play](https://play.google.com/store/apps/details?id=app.alextran.immich)

Configure mobile app:
1. Server URL: `https://photos.${BASE_DOMAIN}`
2. Email/Password: Your Immich credentials
3. Enable auto-backup in app settings

## Deployment Options

### Option 1: Run Both PhotoPrism and Immich
```bash
# Deploy both services
./homelab deploy --only-apps photoprism,immich
```
**Use case:** Evaluate both, choose later

### Option 2: Immich Only
```bash
# Deploy only Immich
./homelab deploy --only-apps immich
```
**Use case:** New installation or committed to Immich

### Option 3: PhotoPrism Only
```bash
# Skip Immich deployment
./homelab deploy --skip-apps immich
```
**Use case:** Committed to PhotoPrism

## Configuration

### Machine Learning Features

Immich uses ML for:
- Facial recognition
- Object detection
- Smart search ("find photos of beaches")
- Duplicate detection

ML processing runs on `immich-machine-learning` service. For GPU acceleration, modify the service:

```yaml
immich-machine-learning:
  image: ghcr.io/immich-app/immich-machine-learning:${IMMICH_VERSION:-release}-cuda  # CUDA version
  deploy:
    placement:
      constraints:
        - node.labels.gpu == true
  environment:
    NVIDIA_VISIBLE_DEVICES: all
    NVIDIA_DRIVER_CAPABILITIES: compute,utility
```

### Video Transcoding

Immich supports hardware acceleration for video transcoding:
- NVIDIA GPU (NVENC)
- Intel QuickSync
- AMD AMF
- Software fallback

Configure in **Administration** → **Settings** → **Video Transcoding**.

### User Management

Create additional users:
1. **Administration** → **Users**
2. Click **Create User**
3. Set email, password, and quota
4. Enable/disable features per user

## Maintenance

### Updating Immich

Update to latest version:

```bash
# Update environment variable (optional)
IMMICH_VERSION=v1.xxx.x

# Redeploy
./homelab deploy --only-apps immich
```

### Database Backup

Backup PostgreSQL database:

```bash
# Find the node running the database
docker service ps immich_immich-postgres --format '{{.Node}}'

# SSH to that node and backup
docker exec immich_immich-postgres.1.xxx \
  pg_dump -U postgres immich > immich_backup_$(date +%Y%m%d).sql
```

### Storage Management

Monitor storage usage:

```bash
# Check upload volume usage
ssh admin@nas.local 'du -sh /srv/immich_upload'

# Check model cache usage
ssh admin@nas.local 'du -sh /srv/immich_model_cache'
```

## Troubleshooting

### ML Features Not Working

**Issue:** Face detection or smart search not functioning

**Solutions:**
1. Check `immich-machine-learning` service logs:
   ```bash
   docker service logs immich_immich-machine-learning
   ```

2. Verify service is running:
   ```bash
   docker service ps immich_immich-machine-learning
   ```

3. Enable jobs in **Administration** → **Jobs**:
   - Face Detection
   - Smart Search
   - Object Detection

### External Library Not Scanning

**Issue:** PhotoPrism photos not appearing

**Solutions:**
1. Verify mount inside container:
   ```bash
   docker exec -it immich_immich-server.1.xxx ls -la /mnt/media/photos
   ```

2. Check CIFS mount credentials in `.env`

3. Verify `all_data` volume exists:
   ```bash
   docker volume inspect immich_all_data
   ```

4. Check library scan logs in **Administration** → **Jobs**

### Mobile App Connection Issues

**Issue:** Cannot connect to server from mobile app

**Solutions:**
1. Verify HTTPS certificate is valid
2. Check Traefik routing:
   ```bash
   docker service logs traefik_traefik | grep immich
   ```
3. Test server URL in browser first
4. Ensure mobile device can resolve `photos.${BASE_DOMAIN}`

### Upload Failures

**Issue:** Photos fail to upload

**Solutions:**
1. Check storage space on NAS:
   ```bash
   ssh admin@nas.local 'df -h /srv/immich_upload'
   ```

2. Verify CIFS mount permissions:
   ```bash
   docker exec -it immich_immich-server.1.xxx touch /usr/src/app/upload/test.txt
   ```

3. Check service logs:
   ```bash
   docker service logs immich_immich-server
   ```

## Services

This stack deploys four services:

| Service | Purpose | Port | Placement |
|---------|---------|------|-----------|
| `immich-server` | Main application | 3001 | Any node |
| `immich-machine-learning` | ML processing | 3003 | Any node (GPU optional) |
| `immich-redis` | Cache layer | 6379 | Any node |
| `immich-postgres` | Database | 5432 | `database` labeled node |

## Migration Paths

### From PhotoPrism to Immich

1. **Stop PhotoPrism:**
   ```bash
   ./homelab teardown --only-apps photoprism
   ```

2. **Update Immich mounts** to use `all_data` as main library:
   ```yaml
   volumes:
     - all_data:/usr/src/app/upload
   ```

3. **Redeploy Immich:**
   ```bash
   ./homelab deploy --only-apps immich
   ```

4. **Scan library** in Immich UI

### From Immich to PhotoPrism

1. **Copy Immich uploads to PhotoPrism:**
   ```bash
   ssh admin@nas.local 'cp -r /srv/immich_upload/* /srv/all_data/'
   ```

2. **Rescan in PhotoPrism UI**

3. **Stop Immich:**
   ```bash
   ./homelab teardown --only-apps immich
   ```

## Resources

- **Official Site:** https://immich.app/
- **Documentation:** https://docs.immich.app/
- **GitHub:** https://github.com/immich-app/immich
- **Discord:** https://discord.immich.app/
- **Mobile Apps:** [iOS](https://apps.apple.com/app/immich/id1613945652) | [Android](https://play.google.com/store/apps/details?id=app.alextran.immich)

## License

- **Immich:** AGPL-3.0
- **PostgreSQL:** PostgreSQL License
- **Redis:** BSD-3-Clause
