# Hardware Constraints Analysis

**Date**: 2025-01-08
**Purpose**: Analysis 11.3 - Investigate respecting node hardware limits in service deployment
**Issue**: [#31](https://github.com/chutch3/selfhosted.sh/issues/31) - Node-Specific Generation

## Executive Summary

This analysis examines how hardware constraints could be incorporated into service deployment decisions, ensuring services are deployed only to nodes that meet their resource requirements. Based on home lab context and existing infrastructure, this analysis recommends minimal constraint awareness.

## 1. Current Hardware Context

### 🖥️ Node Hardware Profiles in Home Labs

#### Typical Home Lab Hardware Variations:
```yaml
# Common home lab node types
hardware_profiles:
  manager_node:
    cpu_cores: 4-8
    memory_gb: 8-32
    storage_gb: 100-1000
    arch: "x86_64"
    gpu: false

  worker_sbc:  # Single Board Computer (Raspberry Pi, etc.)
    cpu_cores: 2-4
    memory_gb: 2-8
    storage_gb: 16-128
    arch: "arm64"
    gpu: false

  worker_desktop:  # Repurposed desktop/laptop
    cpu_cores: 4-16
    memory_gb: 8-64
    storage_gb: 500-2000
    arch: "x86_64"
    gpu: true  # Possible
```

#### Current Infrastructure Definition:
```yaml
# machines.yml.example - No hardware specs currently defined
managers:
  - hostname: manager-1
    ip: 192.168.1.10
    user: ubuntu
    role: manager
    labels:
      - "node.type=manager"
      - "storage.type=local"
    # ❌ No hardware constraints defined

workers:
  - hostname: worker-1
    ip: 192.168.1.11
    user: ubuntu
    role: worker
    labels:
      - "node.type=worker"
      - "storage.type=nfs"
    # ❌ No hardware constraints defined
```

### 🔍 Docker Swarm Hardware Awareness

#### Native Docker Resource Constraints:
```yaml
# Docker Swarm supports resource limits and reservations
services:
  resource_heavy_service:
    deploy:
      resources:
        limits:
          cpus: '2.0'        # ✅ CPU limit
          memory: 4G         # ✅ Memory limit
        reservations:
          cpus: '1.0'        # ✅ CPU reservation
          memory: 2G         # ✅ Memory reservation
      placement:
        constraints:
          - node.labels.storage.type == ssd    # ✅ Hardware-based placement
          - node.labels.arch == x86_64         # ✅ Architecture constraint
```

#### Current Service Resource Usage (Estimated):
```yaml
# Estimated resource requirements for current services
service_resource_estimates:
  homepage:
    cpu_minimal: 0.1        # Dashboard, very light
    memory_mb: 128
    storage_mb: 100

  actual:
    cpu_minimal: 0.2        # Budget app, moderate
    memory_mb: 512
    storage_mb: 1024

  homeassistant:
    cpu_moderate: 0.5       # Automation hub, heavier
    memory_mb: 1024
    storage_mb: 2048

  reverse_proxy:
    cpu_minimal: 0.1        # Nginx, very efficient
    memory_mb: 64
    storage_mb: 50
```

## 2. Hardware Constraint Categories

### 🎯 Resource-Based Constraints

#### CPU Requirements:
```yaml
# Service CPU categorization
cpu_requirements:
  minimal:      # < 0.25 cores
    services: ["homepage", "reverse_proxy", "cryptpad"]
    suitable_nodes: ["manager", "worker_sbc", "worker_desktop"]

  moderate:     # 0.25 - 1.0 cores
    services: ["actual", "homeassistant"]
    suitable_nodes: ["manager", "worker_desktop"]
    unsuitable_nodes: ["worker_sbc"]  # May struggle

  intensive:    # > 1.0 cores
    services: ["media_processing", "machine_learning"]
    suitable_nodes: ["worker_desktop"]
    unsuitable_nodes: ["manager", "worker_sbc"]
```

#### Memory Requirements:
```yaml
# Service memory categorization
memory_requirements:
  low:          # < 512MB
    services: ["homepage", "reverse_proxy"]
    suitable_nodes: ["any"]

  medium:       # 512MB - 2GB
    services: ["actual", "cryptpad"]
    suitable_nodes: ["manager", "worker_desktop"]
    marginal_nodes: ["worker_sbc"]  # Depends on total RAM

  high:         # > 2GB
    services: ["homeassistant", "media_services"]
    suitable_nodes: ["worker_desktop"]
    unsuitable_nodes: ["worker_sbc"]
```

### 🎯 Architecture-Based Constraints

#### CPU Architecture Requirements:
```yaml
# Architecture-specific service constraints
architecture_constraints:
  x86_64_only:
    services: ["proprietary_software", "legacy_applications"]
    constraint: "node.platform.arch == x86_64"

  arm_compatible:
    services: ["homepage", "actual", "homeassistant"]
    constraint: "node.platform.arch in [x86_64, arm64]"

  multi_arch:
    services: ["reverse_proxy", "cryptpad"]
    constraint: "any"  # Available for both architectures
```

#### Implementation Example:
```yaml
# Enhanced services.yaml with architecture constraints
services:
  homepage:
    name: "Homepage Dashboard"
    compose: {...}
    constraints:
      arch: ["x86_64", "arm64"]    # ✅ Multi-architecture
      min_memory_mb: 128
      min_cpu_cores: 0.1

  proprietary_service:
    name: "Proprietary Software"
    compose: {...}
    constraints:
      arch: ["x86_64"]             # ✅ x86_64 only
      min_memory_mb: 2048
      min_cpu_cores: 1.0
```

### 🎯 Storage-Based Constraints

#### Storage Performance Requirements:
```yaml
# Storage performance constraints
storage_constraints:
  high_iops:
    services: ["database_services", "cache_services"]
    required_labels: ["storage.type=ssd"]
    unsuitable_labels: ["storage.type=hdd"]

  high_capacity:
    services: ["media_storage", "backup_services"]
    required_labels: ["storage.capacity=high"]
    min_storage_gb: 500

  low_latency:
    services: ["real_time_services"]
    required_labels: ["storage.type=nvme"]
    max_latency_ms: 5
```

## 3. Hardware Detection and Labeling

### 🔍 Automatic Hardware Detection

#### Docker Swarm Node Information:
```bash
# Docker Swarm provides node information automatically
docker node inspect self --format '{{json .Description.Resources}}'
# Output: {"NanoCPUs":4000000000,"MemoryBytes":8589934592}

docker node inspect self --format '{{json .Description.Platform}}'
# Output: {"Architecture":"x86_64","OS":"linux"}
```

#### Enhanced Machine Definition:
```yaml
# Enhanced machines.yml with hardware detection
managers:
  - hostname: manager-1
    ip: 192.168.1.10
    user: ubuntu
    role: manager
    hardware:                    # ✅ New hardware section
      cpu_cores: 4
      memory_gb: 8
      storage_gb: 500
      arch: "x86_64"
      storage_type: "ssd"
    labels:
      - "hardware.cpu.cores=4"
      - "hardware.memory.gb=8"
      - "hardware.arch=x86_64"
      - "hardware.storage.type=ssd"
```

#### Automatic Label Generation:
```bash
# Hardware detection and labeling script
detect_and_label_hardware() {
    local node_name="$1"

    # Get hardware information
    local cpu_cores
    cpu_cores=$(nproc)
    local memory_gb
    memory_gb=$(($(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024))
    local arch
    arch=$(uname -m)

    # Apply Docker Swarm labels
    docker node update \
        --label-add "hardware.cpu.cores=${cpu_cores}" \
        --label-add "hardware.memory.gb=${memory_gb}" \
        --label-add "hardware.arch=${arch}" \
        "${node_name}"
}
```

### 📋 Manual Hardware Specification

#### Explicit Hardware Configuration:
```yaml
# Manual hardware specification in machines.yml
workers:
  - hostname: pi-worker-1
    ip: 192.168.1.20
    user: pi
    role: worker
    hardware:
      cpu_cores: 4
      cpu_arch: "arm64"
      memory_gb: 4
      storage_gb: 64
      storage_type: "sd_card"    # ✅ Important for constraint decisions
      gpu: false
      network_speed: "gigabit"
    constraints:                 # ✅ Derived constraints
      max_memory_per_service: 1024  # MB
      max_cpu_per_service: 1.0
      avoid_io_intensive: true   # Due to SD card storage
```

## 4. Constraint Implementation Approaches

### 🎯 Approach 1: Service-Level Hardware Requirements

#### Enhanced Service Configuration:
```yaml
# services.yaml with hardware requirements
services:
  lightweight_service:
    name: "Lightweight Service"
    compose: {...}
    hardware_requirements:
      min_cpu_cores: 0.1
      min_memory_mb: 128
      max_memory_mb: 512
      architectures: ["x86_64", "arm64"]
      storage_type: "any"

  intensive_service:
    name: "Intensive Service"
    compose: {...}
    hardware_requirements:
      min_cpu_cores: 2.0
      min_memory_mb: 4096
      max_memory_mb: 8192
      architectures: ["x86_64"]     # x86_64 only
      storage_type: "ssd"           # SSD required
      gpu_required: false
```

#### Constraint Validation Logic:
```bash
# Hardware constraint validation function
validate_hardware_constraints() {
    local service_key="$1"
    local target_node="$2"

    # Get service requirements
    local min_cpu
    min_cpu=$(yq ".services[\"${service_key}\"].hardware_requirements.min_cpu_cores" "$SERVICES_CONFIG")
    local min_memory
    min_memory=$(yq ".services[\"${service_key}\"].hardware_requirements.min_memory_mb" "$SERVICES_CONFIG")

    # Get node capabilities
    local node_cpu
    node_cpu=$(docker node inspect "$target_node" --format '{{.Description.Resources.NanoCPUs}}' | awk '{print $1/1000000000}')
    local node_memory
    node_memory=$(docker node inspect "$target_node" --format '{{.Description.Resources.MemoryBytes}}' | awk '{print $1/1024/1024}')

    # Validate constraints
    if (( $(echo "$node_cpu >= $min_cpu" | bc -l) )) && (( node_memory >= min_memory )); then
        echo "✅ Node $target_node meets hardware requirements for $service_key"
        return 0
    else
        echo "❌ Node $target_node does not meet hardware requirements for $service_key"
        return 1
    fi
}
```

### 🎯 Approach 2: Docker Swarm Placement Integration

#### Enhanced Swarm Generation with Constraints:
```yaml
# Generated Docker Swarm configuration with hardware constraints
services:
  intensive_service:
    image: resource-heavy-app:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
      placement:
        constraints:
          - node.labels.hardware.arch == x86_64       # ✅ Architecture constraint
          - node.labels.hardware.memory.gb >= 8       # ✅ Memory constraint
          - node.labels.hardware.storage.type == ssd  # ✅ Storage constraint
```

#### Generation Logic Enhancement:
```bash
# Enhanced swarm generation with hardware constraints
generate_swarm_with_hardware_constraints() {
    local service_key="$1"

    # Get hardware requirements
    local architectures
    architectures=$(yq ".services[\"${service_key}\"].hardware_requirements.architectures[]?" "$SERVICES_CONFIG")
    local min_memory_gb
    min_memory_gb=$(yq ".services[\"${service_key}\"].hardware_requirements.min_memory_mb" "$SERVICES_CONFIG")
    min_memory_gb=$((min_memory_gb / 1024))  # Convert MB to GB

    # Generate placement constraints
    if [ -n "$architectures" ]; then
        echo "        constraints:"
        for arch in $architectures; do
            echo "          - node.labels.hardware.arch == $arch"
        done

        if [ "$min_memory_gb" -gt 0 ]; then
            echo "          - node.labels.hardware.memory.gb >= $min_memory_gb"
        fi
    fi
}
```

### 🎯 Approach 3: Pre-Deployment Validation

#### Deployment Readiness Check:
```bash
# Pre-deployment hardware validation
validate_deployment_readiness() {
    local deployment_type="$1"  # compose, swarm

    echo "🔍 Validating hardware requirements for $deployment_type deployment..."

    local validation_failed=false

    # Check each enabled service
    while read -r service_key; do
        if ! validate_service_hardware_requirements "$service_key" "$deployment_type"; then
            validation_failed=true
        fi
    done < <(yq '.services | to_entries[] | select(.value.enabled == true) | .key' "$SERVICES_CONFIG")

    if [ "$validation_failed" = true ]; then
        echo "❌ Hardware validation failed. Some services cannot be deployed."
        return 1
    else
        echo "✅ All services meet hardware requirements."
        return 0
    fi
}
```

## 5. Home Lab Hardware Reality

### 🏠 Typical Home Lab Constraints

#### Limited Hardware Diversity:
- **Similar Nodes**: Most home labs have 2-5 similar nodes
- **Uniform Architecture**: Usually all x86_64 or mixed x86_64/ARM
- **Modest Resources**: Typically 4-16GB RAM, 4-8 CPU cores per node
- **Over-Provisioned**: Most services use <10% of available resources

#### Real Hardware Constraints:
```yaml
# Realistic home lab hardware constraints
common_constraints:
  raspberry_pi:
    real_limits:
      - memory_intensive_services: "Avoid >2GB services"
      - io_intensive_services: "SD card limitations"
      - architecture_specific: "ARM64 image availability"
    impact: "Moderate - affects some services"

  old_desktop:
    real_limits:
      - power_consumption: "Higher electricity costs"
      - heat_generation: "Cooling considerations"
      - reliability: "Older hardware failures"
    impact: "Low - usually sufficient resources"

  mini_pc:
    real_limits:
      - memory_upgrade: "Often non-upgradeable"
      - storage_expansion: "Limited expansion slots"
    impact: "Low - good resource density"
```

### 📊 Resource Utilization Analysis

#### Typical Home Lab Resource Usage:
```yaml
# Real-world resource utilization
resource_utilization:
  current_services:
    total_cpu_usage: "10-30%"     # Very low utilization
    total_memory_usage: "20-60%"  # Moderate utilization
    total_storage_usage: "10-40%" # Low to moderate

  constraining_factors:
    primary: "Memory on low-RAM nodes"
    secondary: "Architecture compatibility"
    tertiary: "Storage performance on SD cards"

  optimization_opportunities:
    high_impact: "ARM64 image availability"
    medium_impact: "Memory-efficient service configuration"
    low_impact: "CPU scheduling optimization"
```

## 6. Implementation Cost-Benefit Analysis

### ✅ Benefits of Hardware Constraints

#### Operational Benefits:
- **Resource Protection**: Prevent resource-intensive services on constrained nodes
- **Architecture Compatibility**: Ensure services run on compatible architectures
- **Performance Optimization**: Match services to appropriate hardware capabilities
- **Failure Prevention**: Avoid OOM kills and performance degradation

#### Development Benefits:
- **Explicit Requirements**: Clear documentation of service resource needs
- **Deployment Validation**: Early detection of deployment issues
- **Capacity Planning**: Better understanding of cluster resource requirements

### ❌ Costs of Hardware Constraints

#### Implementation Complexity:
- **Hardware Detection**: Auto-discovery of node capabilities
- **Constraint Configuration**: Defining requirements for each service
- **Validation Logic**: Complex pre-deployment checking
- **Error Handling**: Managing constraint violations

#### Operational Overhead:
- **Configuration Maintenance**: Keeping hardware specs updated
- **Troubleshooting**: Understanding why services won't deploy
- **User Education**: Teaching constraint concepts to users

#### Development Time:
- **Core Implementation**: ~40-60 hours
- **Hardware Detection**: ~20-30 hours
- **Validation System**: ~30-40 hours
- **Documentation**: ~20-30 hours
- **Testing**: ~40-60 hours

**Total Estimated Effort**: ~150-220 hours

## 7. Recommended Approach

### 🎯 Minimal Hardware Awareness (Recommended)

Based on home lab context and cost-benefit analysis:

#### Phase 1: Basic Architecture Support
```yaml
# Minimal architecture awareness
services:
  x86_only_service:
    name: "x86-64 Only Service"
    compose: {...}
    placement:
      architecture: "x86_64"     # ✅ Simple architecture constraint

  multi_arch_service:
    name: "Multi-Architecture Service"
    compose: {...}
    # No constraints - runs anywhere
```

#### Phase 2: Optional Resource Hints
```yaml
# Optional resource guidance (not enforced)
services:
  resource_aware_service:
    name: "Resource Aware Service"
    compose: {...}
    resource_hints:
      recommended_memory_mb: 2048    # ✅ Guidance, not requirement
      recommended_cpu_cores: 1.0
      notes: "Works better with SSD storage"
```

#### Implementation Benefits:
- **✅ Low Complexity**: Minimal additional configuration
- **✅ Backward Compatible**: Existing configurations unchanged
- **✅ User Choice**: Optional enhancement for power users
- **✅ Architecture Focus**: Addresses most common constraint (x86_64 vs ARM)

### 🔧 Simple Implementation

#### Enhanced machines.yml:
```yaml
# Simple hardware labeling
managers:
  - hostname: manager-1
    ip: 192.168.1.10
    user: ubuntu
    role: manager
    labels:
      - "node.type=manager"
      - "arch=x86_64"              # ✅ Simple architecture label
      - "memory.class=high"        # ✅ Simple memory class
```

#### Enhanced Swarm Generation:
```bash
# Simple architecture constraint generation
generate_architecture_constraints() {
    local service_key="$1"
    local required_arch
    required_arch=$(yq ".services[\"${service_key}\"].placement.architecture?" "$SERVICES_CONFIG")

    if [ "$required_arch" != "null" ] && [ -n "$required_arch" ]; then
        echo "      placement:"
        echo "        constraints:"
        echo "          - node.labels.arch == $required_arch"
    fi
}
```

## 8. Conclusion

**✅ Analysis 11.3 COMPLETED**: Hardware constraints investigation completed for home lab context.

### Key Findings

1. **Limited Home Lab Need**: Most home labs have similar hardware with sufficient resources
2. **Architecture Primary Concern**: x86_64 vs ARM compatibility most important constraint
3. **High Implementation Cost**: Full hardware constraint system requires 150-220 hours
4. **Low ROI**: Benefit doesn't justify complex implementation for home lab scale

### Recommendation

**✅ MINIMAL HARDWARE AWARENESS**: Focus on architecture compatibility with optional resource hints.

#### Implementation Plan:
1. **Phase 1**: Add optional architecture constraints to services.yaml
2. **Phase 2**: Add simple resource hints for documentation
3. **Phase 3**: Enhance Docker Swarm generation with architecture constraints

#### Decision Rationale:
- **Appropriate Scale**: Minimal enhancement matches home lab hardware reality
- **Architecture Focus**: Addresses most common real constraint
- **Low Complexity**: Minimal development and operational overhead
- **User-Friendly**: Easy to understand and configure

**Issue #31 Summary**: Node-specific generation analysis complete. Recommend minimal role-based and hardware-aware enhancements focused on home lab practicality.

**Next Step**: Begin Issue #32 - Configuration Orchestration analysis.
