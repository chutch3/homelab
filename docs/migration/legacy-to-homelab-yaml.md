# Migration Guide: Legacy Configuration to homelab.yaml

**Purpose**: Guide for migrating from legacy multi-file configuration (`services.yaml` + `machines.yaml` + `volumes.yaml` + `.env`) to the unified `homelab.yaml` format.

## Overview

The migration tool automatically converts your existing configuration files to the new unified `homelab.yaml` format, preserving all essential service definitions and deployment settings while simplifying the overall configuration structure.

## What Gets Migrated

### Input Files (Legacy Format)
- **`config/services.yaml`** - Service definitions, container configs, and deployment settings
- **`machines.yaml`** - Multi-node infrastructure definitions (managers/workers)
- **`config/volumes.yaml`** - Storage and volume configurations
- **`.env`** - Environment variables and secrets

### Output File (New Format)
- **`homelab.yaml`** - Unified configuration with all settings

## Migration Process

### Basic Migration

```bash
# Dry run to preview changes
./scripts/migrate_to_homelab_yaml.sh --dry-run

# Migrate to default homelab.yaml
./scripts/migrate_to_homelab_yaml.sh

# Migrate for Docker Swarm deployment
./scripts/migrate_to_homelab_yaml.sh --deployment docker_swarm
```

### Migration Options

| Option | Description | Example |
|--------|-------------|---------|
| `--dry-run` | Preview migration without creating files | `--dry-run` |
| `--deployment TYPE` | Target deployment type | `--deployment docker_swarm` |
| `--output FILE` | Custom output file | `--output my-config.yaml` |
| `--force` | Overwrite existing output file | `--force` |
| `--validate` | Validate output after migration | `--validate` |
| `--services FILE` | Custom services file | `--services custom-services.yaml` |
| `--machines FILE` | Custom machines file | `--machines custom-machines.yaml` |

### Advanced Migration

```bash
# Custom input files with validation
./scripts/migrate_to_homelab_yaml.sh \
  --services config/my-services.yaml \
  --machines my-machines.yaml \
  --output production-homelab.yaml \
  --deployment docker_swarm \
  --validate \
  --force

# Preview complex migration
./scripts/migrate_to_homelab_yaml.sh \
  --dry-run \
  --deployment docker_compose \
  --services config/services.yaml
```

## Migration Mapping

### Services Configuration

#### Legacy Format (`services.yaml`)
```yaml
services:
  actual:
    name: Actual Budget
    port: 5006
    compose:
      image: actualbudget/actual-server:latest
      ports: ["5006:5006"]
      environment:
        - DEBUG=actual:config
      volumes:
        - /mnt/app_data/budget:/data
    nginx:
      upstream: actual_server:5006
    enabled: true
```

#### New Format (`homelab.yaml`)
```yaml
services:
  actual:
    image: actualbudget/actual-server:latest
    port: 5006
    storage: true
    environment:
      DEBUG: "actual:config"
    overrides:
      docker_compose:
        volumes:
          - "/mnt/app_data/budget:/data"
```

### Machine Configuration

#### Legacy Format (`machines.yaml`)
```yaml
managers:
  - hostname: "manager1.local"
    ip: "192.168.1.100"
    user: "ubuntu"
    role: "manager"
    labels:
      environment: "production"

workers:
  - hostname: "worker1.local"
    ip: "192.168.1.101"
    user: "ubuntu"
    role: "worker"
```

#### New Format (`homelab.yaml`)
```yaml
machines:
  manager1:
    host: 192.168.1.100
    user: ubuntu
    role: manager
    labels:
      - "environment=production"

  worker1:
    host: 192.168.1.101
    user: ubuntu
    role: worker
```

### Environment Variables

#### Legacy Format (`.env`)
```bash
BASE_DOMAIN=homelab.local
PROJECT_ROOT=/opt/homelab
DB_PASSWORD=secret123
```

#### New Format (`homelab.yaml`)
```yaml
environment:
  BASE_DOMAIN: homelab.local
  PROJECT_ROOT: /opt/homelab
  DB_PASSWORD: secret123
```

## Migration Behavior

### Service Processing
1. **Image Extraction**: Pulls from `compose.image` or `container.image`
2. **Port Detection**: Uses `port` field or extracts from `compose.ports`
3. **Storage Detection**: Sets `storage: true` if volumes are present
4. **Environment Variables**: Converts arrays and objects to unified format
5. **Complex Configurations**: Moves to `overrides` section

### Machine Processing
1. **Name Generation**: Creates machine names from hostnames (removes domain)
2. **Role Assignment**: Preserves manager/worker roles for Docker Swarm
3. **Label Conversion**: Converts key-value objects to "key=value" array format
4. **Default Creation**: Creates `driver: localhost` if no machines file exists

### Environment Processing
1. **Variable Export**: Loads all environment variables for template expansion
2. **Readonly Handling**: Skips `UID` and `GID` to avoid conflicts
3. **Quote Removal**: Strips quotes from values
4. **Comment Filtering**: Ignores commented and empty lines

## Migration Results

### Successful Migration Output
```bash
[INFO] Starting migration from legacy configuration to homelab.yaml
[INFO] Target deployment type: docker_compose
[INFO] Processing machines configuration from machines.yaml
[INFO] Processing environment variables from .env
[INFO] Processing services configuration from config/services.yaml
[INFO] Processing service: actual
[INFO] Processing service: homepage
[SUCCESS] Migration completed successfully
[INFO] Generated: homelab.yaml

Next steps:
  1. Review the generated homelab.yaml
  2. Validate: ./scripts/simple_homelab_validator.sh homelab.yaml
  3. Test deployment with new configuration
  4. Backup and remove legacy files when satisfied
```

### Common Issues and Solutions

#### Issue: yq Parsing Errors
**Symptoms**: Multiple parsing errors during migration
**Cause**: Complex YAML structures or malformed configuration
**Solution**: Check original YAML files for syntax errors

```bash
# Validate original files
yq . config/services.yaml
yq . machines.yaml
yq . config/volumes.yaml
```

#### Issue: Missing Services
**Symptoms**: Some services not included in output
**Cause**: Services marked as `enabled: false`
**Solution**: Enable services or manually add them

```yaml
# In services.yaml, ensure:
services:
  myservice:
    enabled: true  # Make sure this is true
```

#### Issue: Complex Configurations Lost
**Symptoms**: Advanced Docker configurations missing
**Cause**: Migration simplified complex setups
**Solution**: Review `overrides` section and add missing configurations

```yaml
# Add missing configurations to overrides
services:
  myservice:
    overrides:
      docker_compose:
        depends_on: ["database"]
        networks: ["custom"]
        restart: unless-stopped
```

#### Issue: Machine Names Incorrect
**Symptoms**: Generated machine names don't match expectations
**Cause**: Automatic name generation from hostnames
**Solution**: Manually adjust machine names in output

```yaml
# Change from:
machines:
  manager1local:  # Auto-generated
    host: 192.168.1.100

# To:
machines:
  manager-01:     # Manually adjusted
    host: 192.168.1.100
```

## Post-Migration Tasks

### 1. Validation
```bash
# Validate generated configuration
./scripts/simple_homelab_validator.sh homelab.yaml

# Or with full schema validation (if available)
./scripts/validate_homelab_schema.sh homelab.yaml
```

### 2. Review and Adjust
- **Service Names**: Ensure they match your preferences
- **Machine Names**: Adjust to your naming convention
- **Port Mappings**: Verify all ports are correctly extracted
- **Storage Paths**: Check that volume mappings are preserved
- **Environment Variables**: Confirm all secrets are included

### 3. Test Deployment
```bash
# Test with new configuration (future implementation)
./selfhosted.sh deploy --config homelab.yaml --dry-run
```

### 4. Backup Legacy Files
```bash
# Create backup directory
mkdir -p backups/legacy-config-$(date +%Y%m%d)

# Backup original files
cp config/services.yaml backups/legacy-config-$(date +%Y%m%d)/
cp machines.yaml backups/legacy-config-$(date +%Y%m%d)/ 2>/dev/null || true
cp config/volumes.yaml backups/legacy-config-$(date +%Y%m%d)/
cp .env backups/legacy-config-$(date +%Y%m%d)/ 2>/dev/null || true
```

## Migration Examples

### Example 1: Basic Single-Machine Setup
```bash
# Legacy: services.yaml only
./scripts/migrate_to_homelab_yaml.sh --dry-run

# Result: Simple homelab.yaml with driver machine
```

### Example 2: Multi-Node Docker Compose
```bash
# Legacy: services.yaml + machines.yaml
./scripts/migrate_to_homelab_yaml.sh \
  --deployment docker_compose \
  --validate
```

### Example 3: Docker Swarm Cluster
```bash
# Legacy: Full configuration with swarm settings
./scripts/migrate_to_homelab_yaml.sh \
  --deployment docker_swarm \
  --output swarm-homelab.yaml \
  --validate
```

## Troubleshooting

### Debug Migration Issues
```bash
# Run with verbose debugging
bash -x ./scripts/migrate_to_homelab_yaml.sh --dry-run 2>&1 | less

# Check specific file issues
yq '.services.problematic_service' config/services.yaml
```

### Manual Migration Steps
If automatic migration fails, you can manually create sections:

1. **Start with basic structure**:
```yaml
version: "2.0"
deployment: docker_compose
environment: {}
machines: {}
services: {}
```

2. **Copy services one by one** from legacy configuration
3. **Validate each addition** using the validation script
4. **Test incrementally** to identify issues

### Getting Help
- **Validation Errors**: Use the validation tools to identify specific issues
- **Complex Configurations**: Review the homelab.yaml reference documentation
- **Migration Bugs**: Check that input files have valid YAML syntax

## Best Practices

### Before Migration
1. **Backup Everything**: Ensure you have backups of all configuration files
2. **Test Environment**: Run migration in a test environment first
3. **Document Customizations**: Note any custom configurations that need manual handling

### During Migration
1. **Use Dry Run**: Always preview changes before applying
2. **Validate Output**: Use validation tools to check generated configuration
3. **Review Carefully**: Examine the generated file for accuracy

### After Migration
1. **Test Thoroughly**: Verify all services work with new configuration
2. **Monitor Deployment**: Watch for any issues in the first deployment
3. **Keep Backups**: Retain legacy files until confident in new setup

## Migration Checklist

- [ ] Backup all legacy configuration files
- [ ] Run migration with `--dry-run` to preview changes
- [ ] Review generated `homelab.yaml` for accuracy
- [ ] Validate configuration using validation tools
- [ ] Test deployment in staging environment
- [ ] Migrate production environment
- [ ] Verify all services are working correctly
- [ ] Archive legacy configuration files
- [ ] Update documentation and procedures

---

**Note**: The migration tool handles most common configurations automatically, but complex setups may require manual adjustments. Always review the generated configuration before deploying to production.
