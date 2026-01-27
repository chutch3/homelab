# Forgejo Stack

Self-hosted Git service (Forgejo fork of Gitea) with PostgreSQL database backend.

## Overview

Forgejo is a self-hosted lightweight software forge providing Git hosting, issue tracking, pull requests, wikis, and more. This stack deploys Forgejo with PostgreSQL database using ISCSI storage for data persistence.

## Services

- **forgejo**: Main Forgejo application server (rootless container)
- **forgejo-db**: PostgreSQL 16 database

## Access

- **Web UI**: `https://git.${BASE_DOMAIN}/`
- **SSH**: Port `${FORGEJO_SSH_PORT:-2222}`

## Prerequisites

### 1. Create ISCSI Directories

Create the required directories on your ISCSI mount:

```bash
sudo mkdir -p /mnt/iscsi/app-data/forgejo/{postgresql,data,config}
sudo chown -R 1000:1000 /mnt/iscsi/app-data/forgejo/{data,config}
sudo chown -R 999:999 /mnt/iscsi/app-data/forgejo/postgresql
```

### 2. Environment Variables

Add the following variables to your `.env` file:

```bash
# Forgejo Configuration
FORGEJO_VERSION=10-rootless
FORGEJO_SSH_PORT=2222

# Database Configuration
FORGEJO_DB_USER=forgejo
FORGEJO_DB_PASSWORD=your-secure-password-here
FORGEJO_DB_NAME=forgejo

# Optional: Authentik OIDC (if using SSO)
# FORGEJO_OAUTH_CLIENT_ID=your-client-id
# FORGEJO_OAUTH_CLIENT_SECRET=your-client-secret
```

## Deployment

### 1. Deploy the Stack

```bash
task ansible:deploy:stack -- -e "stack_name=forgejo"
```

### 2. Configure DNS Records

Add the DNS record for Forgejo:

```bash
task ansible:configure:dns
```

This creates the CNAME record: `git.${BASE_DOMAIN}` → `traefik.${BASE_DOMAIN}`

### 3. Configure Uptime Monitoring

Add Forgejo to Uptime Kuma monitoring:

```bash
task ansible:configure:uptime
```

This creates an HTTP monitor for `https://git.${BASE_DOMAIN}/`

## Initial Setup

1. Navigate to `https://git.${BASE_DOMAIN}/`
2. Complete the initial installation wizard:
   - Database settings should be pre-configured
   - Set your administrator account details
   - Configure application settings as needed

## SSH Access

Users can clone repositories using SSH on port 2222 (or your configured port):

```bash
git clone ssh://git@git.${BASE_DOMAIN}:2222/username/repository.git
```

To use the standard SSH port (22), set `FORGEJO_SSH_PORT=22` in your environment variables.

## Authentik SSO Integration (Optional)

Enable single sign-on with Authentik for centralized authentication and group-based admin rights.

### 1. Create Groups Scope Mapping (One-Time Setup)

Check if a groups scope already exists in Authentik:

1. Go to **Customization** → **Property Mappings**
2. Look for scope name `groups` (common names: `Groups Scope`, `goauthentik.io/providers/oauth2/scope-groups`)

If it doesn't exist, create it:
- Click **Create** → **Scope Mapping**
- **Name**: `Groups Scope`
- **Scope name**: `groups`
- **Expression**:
  ```python
  return {
      "groups": [group.name for group in user.ak_groups.all()]
  }
  ```

### 2. Create OAuth2 Provider in Authentik

1. Go to **Applications** → **Providers** → **Create** → **OAuth2/OpenID Provider**
2. Configure:
   - **Name**: `Forgejo`
   - **Client type**: `Confidential`
   - **Redirect URIs**: `https://git.${BASE_DOMAIN}/user/oauth2/Authentik/callback`
   - **Property Mappings**: Select all default OpenID mappings (`openid`, `email`, `profile`) + **Groups Scope**
3. Copy the **Client ID** and **Client Secret**

### 3. Create Admin Group (Optional)

To auto-grant admin rights via SSO:

1. Go to **Directory** → **Groups** → **Create**
2. **Name**: `forgejo-admins`
3. Add users to this group

### 4. Create Application in Authentik

1. Go to **Applications** → **Applications** → **Create**
2. Configure:
   - **Name**: `Forgejo`
   - **Slug**: `forgejo`
   - **Provider**: Select the Forgejo provider
   - **Launch URL**: `https://git.${BASE_DOMAIN}/`

### 5. Update Environment Variables

Add to your `.env` file:
```bash
FORGEJO_OAUTH_CLIENT_ID=<client-id-from-step-2>
FORGEJO_OAUTH_CLIENT_SECRET=<client-secret-from-step-2>
```

### 6. Redeploy Forgejo

```bash
task ansible:deploy:stack -- -e "stack_name=forgejo"
```

### 7. Configure OAuth in Forgejo

After deployment, go to **Site Administration** → **Authentication Sources** → **Add Authentication Source**:

**Basic Configuration:**
- **Authentication Type**: `OAuth2`
- **Authentication Name**: `Authentik`
- **OAuth2 Provider**: `OpenID Connect`
- **Client ID**: (from step 5)
- **Client Secret**: (from step 5)
- **OpenID Connect Auto Discovery URL**: `https://auth.${BASE_DOMAIN}/application/o/forgejo/.well-known/openid-configuration`

**Group Mapping (for admin rights):**
- **Additional scopes**: `groups`
- **Claim name providing group names**: `groups`
- **Group claim value for administrator users**: `forgejo-admins`

**Options:**
- ✓ Enable this authentication source
- ✓ Skip local 2FA (optional)

### 8. Link Existing Accounts (Optional)

To link an existing local account to Authentik SSO:

1. Log in with your local account
2. Go to **Settings** → **Account** → **Link External Accounts**
3. Click **Link Account** next to **Authentik**
4. Authenticate with Authentik

This preserves your existing account while enabling SSO login.

## Storage Locations

- **PostgreSQL Data**: `/mnt/iscsi/app-data/forgejo/postgresql`
- **Git Repositories**: `/mnt/iscsi/app-data/forgejo/data`
- **Configuration**: `/mnt/iscsi/app-data/forgejo/config`

## Backup

The Kopia backup system will automatically back up:
- Git repositories in `/mnt/iscsi/app-data/forgejo/data`
- Configuration files in `/mnt/iscsi/app-data/forgejo/config`

**Note**: The PostgreSQL database directory (`/mnt/iscsi/app-data/forgejo/postgresql`) is excluded from Kopia backups to prevent inconsistent file-based backups of live databases. See the Kopia README for configuration details.

For database backups, consider implementing `pg_dump` backups in the future.

## Maintenance

### View Logs

```bash
docker service logs forgejo_forgejo -f
docker service logs forgejo_forgejo-db -f
```

### Update Forgejo

1. Update the `FORGEJO_VERSION` in your `.env` file
2. Redeploy the stack:
   ```bash
   task ansible:deploy:stack -- -e "stack_name=forgejo"
   ```

### Database Backup

```bash
# Determine which node is running the database
docker service ps forgejo_forgejo-db --filter "desired-state=running" --format "{{.Node}}"

# Then run backup on that node
task ansible:cmd HOST=<node-name> -- docker exec \$(docker ps -q -f name=forgejo_forgejo-db) pg_dump -U forgejo forgejo > forgejo-backup-\$(date +%Y%m%d).sql
```

### Database Restore

```bash
# Run on the node where the database is running
task ansible:cmd HOST=<node-name> -- docker exec -i \$(docker ps -q -f name=forgejo_forgejo-db) psql -U forgejo forgejo < forgejo-backup.sql
```

## Troubleshooting

### SSH Connection Issues

If SSH connections fail:
1. Verify the port is accessible: `nc -zv git.${BASE_DOMAIN} 2222`
2. Check firewall rules allow the SSH port
3. Verify the `FORGEJO__server__SSH_PORT` matches your published port

### Permission Issues

If you see permission errors:
```bash
# Fix ownership for Forgejo data directories
sudo chown -R 1000:1000 /mnt/iscsi/app-data/forgejo/{data,config}

# Fix ownership for PostgreSQL data
sudo chown -R 999:999 /mnt/iscsi/app-data/forgejo/postgresql
```

### Database Connection Issues

Check database connectivity and logs:
```bash
# View database logs
docker service logs forgejo_forgejo-db -f

# View Forgejo application logs
docker service logs forgejo_forgejo -f
```

### SSO Login Fails

If Authentik SSO login fails:
1. Verify callback URL in Authentik matches: `https://git.${BASE_DOMAIN}/user/oauth2/Authentik/callback`
2. Check the `/Authentik/` part matches the **Authentication Name** in Forgejo (case-sensitive)
3. Verify the Groups Scope is added to the provider's Property Mappings
4. Check Forgejo logs:
   ```bash
   docker service logs forgejo_forgejo -f
   ```

### Users Don't Get Admin Rights via SSO

If users in `forgejo-admins` group don't get admin rights:
1. Verify user is in the `forgejo-admins` group in Authentik
2. Check "Claim name providing group names" is set to `groups`
3. Check "Group claim value for administrator users" is set to `forgejo-admins`
4. User may need to log out and log back in for group changes to take effect

## Resources

- [Forgejo Documentation](https://forgejo.org/docs/latest/)
- [Forgejo Installation Guide](https://forgejo.org/docs/latest/admin/installation/)
- [Forgejo Configuration Cheat Sheet](https://forgejo.org/docs/latest/admin/config-cheat-sheet/)
