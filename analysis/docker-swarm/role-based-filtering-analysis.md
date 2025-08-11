# Role-Based Service Filtering Analysis

**Date**: 2025-01-08
**Purpose**: Analysis 11.2 - Investigate filtering services by node role
**Issue**: [#31](https://github.com/chutch3/selfhosted.sh/issues/31) - Node-Specific Generation

## Executive Summary

This analysis examines how role-based service filtering could be implemented to deploy different services to different node roles (manager vs worker), building on the findings from Analysis 11.1 that recommended minimal enhancement over complex node-specific generation.

## 1. Current Node Role Architecture

### 🏗️ Existing Docker Swarm Roles

#### Node Role Definitions:
```yaml
# machines.yml.example structure
managers:
  - hostname: manager-1
    ip: 192.168.1.10
    user: ubuntu
    role: manager          # ✅ Manager node role
    labels:
      - "node.type=manager"
      - "storage.type=local"

workers:
  - hostname: worker-1
    ip: 192.168.1.11
    user: ubuntu
    role: worker           # ✅ Worker node role
    labels:
      - "node.type=worker"
      - "storage.type=nfs"
```

#### Docker Swarm Native Roles:
- **Manager Nodes**: Cluster management, scheduling decisions, maintain cluster state
- **Worker Nodes**: Run containerized applications, receive tasks from managers

### 🔍 Current Service Deployment Behavior

#### Uniform Deployment (Current):
```yaml
# All services currently deploy without role constraints
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    # No role constraints - can run on any node
  actual:
    image: actualbudget/actual-server:latest
    # No role constraints - can run on any node
```

#### Docker Swarm Placement (Available but Unused):
```yaml
# Docker Swarm supports role-based placement (not currently used)
services:
  management_service:
    deploy:
      placement:
        constraints:
          - node.role == manager    # ✅ Manager-only placement
  application_service:
    deploy:
      placement:
        constraints:
          - node.role == worker     # ✅ Worker-only placement
```

## 2. Role-Based Service Categories

### 🎯 Infrastructure Services (Manager Node Candidates)

#### Characteristics:
- **High Availability Requirements**: Should survive worker node failures
- **Cluster Management**: Services that manage other services
- **Security Critical**: Authentication, reverse proxy, monitoring
- **State Management**: Services that maintain cluster state

#### Current Services Analysis:
```yaml
# Services that could benefit from manager node placement
infrastructure_services:
  reverse_proxy:
    justification: "Entry point for all traffic, should be highly available"
    placement_benefit: "Survives worker node failures"

  homepage:
    justification: "Central dashboard for service discovery"
    placement_benefit: "Always available for cluster overview"

  monitoring:
    justification: "Cluster health monitoring and alerting"
    placement_benefit: "Can monitor worker node health"
```

### 🎯 Application Services (Worker Node Candidates)

#### Characteristics:
- **Resource Intensive**: CPU, memory, or storage intensive workloads
- **Scalable**: Can benefit from horizontal scaling across workers
- **Isolated**: Failures don't affect cluster management
- **User-Facing**: End-user applications and data processing

#### Current Services Analysis:
```yaml
# Services that could benefit from worker node placement
application_services:
  actual:
    justification: "User application, resource usage varies"
    placement_benefit: "Doesn't consume manager node resources"

  homeassistant:
    justification: "Heavy automation processing, device integration"
    placement_benefit: "Isolated from cluster management functions"

  media_services:
    justification: "Storage and processing intensive"
    placement_benefit: "Can scale across multiple worker nodes"
```

### 🎯 Flexible Services (Any Node)

#### Characteristics:
- **Lightweight**: Minimal resource requirements
- **Non-Critical**: Can be interrupted without major impact
- **Development/Testing**: Experimental or development services

#### Current Services Analysis:
```yaml
# Services that work well on any node
flexible_services:
  cryptpad:
    justification: "Lightweight collaborative editor"
    placement_benefit: "Can run anywhere as needed"

  development_tools:
    justification: "Development and testing services"
    placement_benefit: "Flexibility for experimentation"
```

## 3. Implementation Approaches

### 🎯 Approach 1: Service-Level Role Specification

#### Implementation in services.yaml:
```yaml
services:
  reverse_proxy:
    name: "Reverse Proxy"
    compose: {...}
    placement:
      roles: ["manager"]           # ✅ Manager nodes only
      mode: "required"             # ✅ Strict requirement

  homepage:
    name: "Homepage Dashboard"
    compose: {...}
    placement:
      roles: ["manager"]           # ✅ Prefer managers
      mode: "preferred"            # ✅ Can fallback to workers

  actual:
    name: "Actual Budget"
    compose: {...}
    placement:
      roles: ["worker"]            # ✅ Worker nodes only
      mode: "required"             # ✅ Strict requirement

  cryptpad:
    name: "CryptPad"
    compose: {...}
    # No placement specified - can run on any node
```

#### Generation Logic:
```bash
# Enhanced generation with role filtering
generate_compose_with_roles() {
    local service_key="$1"
    local target_role="$2"  # manager, worker, or any

    # Get service role requirements
    local service_roles
    service_roles=$(yq ".services[\"${service_key}\"].placement.roles[]?" "$SERVICES_CONFIG")
    local placement_mode
    placement_mode=$(yq ".services[\"${service_key}\"].placement.mode" "$SERVICES_CONFIG")

    # Check if service should be included for this role
    if should_include_service_for_role "$service_key" "$target_role" "$service_roles" "$placement_mode"; then
        generate_service_config "$service_key"
    else
        echo "  Skipping $service_key for $target_role nodes"
    fi
}
```

### 🎯 Approach 2: Role-Specific Generation Files

#### Multiple Output Files:
```bash
# Generate role-specific deployment files
generated-docker-compose-manager.yaml    # ✅ Manager-specific services
generated-docker-compose-worker.yaml     # ✅ Worker-specific services
generated-docker-compose-all.yaml        # ✅ Services for all nodes
```

#### Implementation:
```bash
# Role-specific generation functions
generate_manager_compose() {
    echo "🔧 Generating manager node services..."
    generate_compose_for_role "manager"
}

generate_worker_compose() {
    echo "🔧 Generating worker node services..."
    generate_compose_for_role "worker"
}

generate_compose_for_role() {
    local target_role="$1"
    local output_file="generated-docker-compose-${target_role}.yaml"

    # Process services for specific role
    yaml_parser get-services "$SERVICES_CONFIG" | while read -r service_key; do
        if service_matches_role "$service_key" "$target_role"; then
            add_service_to_compose "$service_key" "$output_file"
        fi
    done
}
```

### 🎯 Approach 3: Docker Swarm Constraint Integration

#### Enhanced Swarm Generation:
```yaml
# services.yaml with Docker Swarm constraints
services:
  reverse_proxy:
    name: "Reverse Proxy"
    swarm:
      deploy:
        mode: global              # ✅ Run on all nodes
        placement:
          constraints:
            - node.role == manager # ✅ Manager nodes only

  application_service:
    name: "Application Service"
    swarm:
      deploy:
        mode: replicated
        replicas: 2
        placement:
          constraints:
            - node.role == worker  # ✅ Worker nodes only
```

#### Generation Enhancement:
```bash
# Enhanced swarm generation with role constraints
generate_swarm_with_roles() {
    local service_key="$1"

    # Get role-based placement from services.yaml
    local role_constraint
    role_constraint=$(yq ".services[\"${service_key}\"].placement.roles[0]" "$SERVICES_CONFIG")

    if [ "$role_constraint" != "null" ] && [ -n "$role_constraint" ]; then
        # Add Docker Swarm constraint
        cat >> "$SWARM_STACK" <<EOF
    deploy:
      placement:
        constraints:
          - node.role == $role_constraint
EOF
    fi
}
```

## 4. Role Assignment Strategy

### 🧠 Intelligent Role Assignment

#### Service Characteristics Analysis:
```yaml
# Automatic role assignment based on service characteristics
role_assignment_rules:
  manager_indicators:
    - service_type: "reverse_proxy"
    - service_type: "monitoring"
    - service_type: "dashboard"
    - high_availability: true
    - cluster_management: true

  worker_indicators:
    - resource_intensive: true
    - scalable: true
    - user_application: true
    - media_processing: true

  flexible_indicators:
    - lightweight: true
    - development: true
    - experimental: true
```

#### Automatic Assignment Logic:
```bash
# Automatic role assignment function
assign_service_role() {
    local service_key="$1"

    # Get service metadata
    local category
    category=$(yq ".services[\"${service_key}\"].category" "$SERVICES_CONFIG")
    local name
    name=$(yq ".services[\"${service_key}\"].name" "$SERVICES_CONFIG")

    # Apply assignment rules
    case "$category" in
        "core"|"infrastructure")
            echo "manager"
            ;;
        "media"|"productivity"|"development")
            echo "worker"
            ;;
        *)
            echo "any"
            ;;
    esac
}
```

### 📋 Manual Role Assignment

#### Explicit Configuration:
```yaml
# Manual role assignment in services.yaml
services:
  critical_service:
    placement:
      roles: ["manager"]
      mode: "required"
      reason: "High availability required"

  scalable_service:
    placement:
      roles: ["worker"]
      mode: "preferred"
      reason: "Resource intensive, can scale"
```

## 5. Implementation Complexity Analysis

### 📊 Development Effort Assessment

#### Core Implementation:
- **Service Role Schema**: Add placement configuration to services.yaml (~8 hours)
- **Generation Logic**: Enhance generators with role filtering (~24 hours)
- **Docker Swarm Integration**: Add constraint generation (~16 hours)
- **CLI Enhancement**: Add role-specific commands (~16 hours)
- **Testing**: Role-based deployment testing (~24 hours)

**Total Estimated Effort**: ~88 hours

#### Additional Features:
- **Automatic Role Assignment**: Intelligent role detection (~32 hours)
- **Role Validation**: Ensure role assignments are valid (~16 hours)
- **Migration Tools**: Convert existing deployments (~16 hours)
- **Documentation**: User guides and examples (~16 hours)

**Total with Enhancements**: ~168 hours

### 🔧 Technical Complexity

#### Configuration Complexity:
```yaml
# Current simple configuration
services:
  service_name:
    enabled: true
    compose: {...}

# Enhanced with role-based placement
services:
  service_name:
    enabled: true
    compose: {...}
    placement:
      roles: ["manager", "worker"]  # New complexity
      mode: "preferred"             # New decision point
      constraints: [...]            # Additional options
```

#### Generation Logic Complexity:
- **Multiple Decision Points**: Role requirements, placement modes, fallback options
- **Cross-Dependencies**: Role assignments affect other services
- **Target-Specific Logic**: Different rules for Compose vs Swarm vs manual deployment

## 6. Benefits vs Costs Analysis

### ✅ Benefits of Role-Based Filtering

#### Operational Benefits:
- **Resource Optimization**: Critical services on stable manager nodes
- **High Availability**: Infrastructure services survive worker node failures
- **Performance**: Resource-intensive services don't impact cluster management
- **Security**: Sensitive services isolated on manager nodes

#### Management Benefits:
- **Clear Service Placement**: Explicit rules about where services run
- **Maintenance Windows**: Can take down workers without affecting core infrastructure
- **Scaling Strategy**: Clear distinction between infrastructure and application scaling

### ❌ Costs of Role-Based Filtering

#### Implementation Costs:
- **Development Time**: ~88-168 hours for complete implementation
- **Testing Complexity**: Must test all role combinations and failure scenarios
- **Migration Effort**: Existing deployments need updating

#### Operational Costs:
- **Configuration Complexity**: Users must understand role assignments
- **Debugging Difficulty**: Services might not deploy due to role constraints
- **Maintenance Overhead**: Role assignments need ongoing management

#### User Experience Costs:
- **Learning Curve**: Users must understand manager vs worker concepts
- **Decision Fatigue**: Every service needs role assignment decision
- **Troubleshooting**: More complex failure modes

## 7. Home Lab Context Assessment

### 🏠 Typical Home Lab Characteristics

#### Scale Factors:
- **Node Count**: Usually 2-5 nodes
- **Manager/Worker Ratio**: Often 1-2 managers, 1-3 workers
- **Hardware Similarity**: Nodes often have similar capabilities
- **Resource Utilization**: Typically low (<50% on most nodes)

#### Usage Patterns:
- **Service Count**: 5-20 services typically
- **Change Frequency**: Regular experimentation and updates
- **Maintenance**: Periodic updates and restarts
- **User Base**: Usually 1-2 administrators

### 🎯 Role-Based Benefits in Home Lab Context

#### Limited Manager/Worker Distinction:
- **Small Scale**: Benefits diminish with only 2-3 total nodes
- **Similar Hardware**: Less differentiation between manager and worker capabilities
- **Low Resource Pressure**: Most services can run anywhere without issues

#### Operational Overhead vs Benefits:
- **High Setup Cost**: Role assignment requires careful planning
- **Low Failure Recovery**: Home labs can afford temporary full outages
- **Maintenance Flexibility**: Often prefer ability to move services freely

## 8. Recommended Implementation

### 🎯 Minimal Role-Based Enhancement

Based on home lab context and cost-benefit analysis:

#### Phase 1: Optional Docker Swarm Constraints
```yaml
# Add optional role constraints to services.yaml
services:
  reverse_proxy:
    name: "Reverse Proxy"
    swarm:  # Only affects Swarm deployments
      deploy:
        mode: global
        placement:
          constraints:
            - node.role == manager  # ✅ Optional constraint
    # Docker Compose behavior unchanged
```

#### Phase 2: Simple Role Preference
```yaml
# Add simple role preference (not requirement)
services:
  infrastructure_service:
    placement:
      preferred_role: "manager"     # ✅ Hint, not requirement
      reason: "High availability"  # ✅ Documentation
```

#### Implementation Benefits:
- **✅ Backward Compatible**: Existing configurations continue to work
- **✅ Optional Enhancement**: Users can opt-in to role awareness
- **✅ Docker Native**: Uses existing Docker Swarm placement capabilities
- **✅ Low Complexity**: Minimal additional configuration required

### 📋 Enhanced Generation Logic

#### Role-Aware Swarm Generation:
```bash
# Enhanced swarm generation with optional role constraints
generate_swarm_with_optional_roles() {
    local service_key="$1"

    # Check for preferred role
    local preferred_role
    preferred_role=$(yq ".services[\"${service_key}\"].placement.preferred_role?" "$SERVICES_CONFIG")

    if [ "$preferred_role" != "null" ] && [ -n "$preferred_role" ]; then
        # Add soft constraint (preference, not requirement)
        echo "      # Preferred placement: $preferred_role nodes"
        echo "      placement:"
        echo "        preferences:"
        echo "          - spread: node.role.$preferred_role"
    fi
}
```

## 9. Conclusion

**✅ Analysis 11.2 COMPLETED**: Role-based service filtering investigated for home lab context.

### Key Findings

1. **Limited Home Lab Benefit**: Role-based filtering provides minimal benefit at home lab scale
2. **Implementation Complexity**: Significant development and operational overhead
3. **Docker Native Support**: Existing Docker Swarm constraints can handle role placement
4. **Optional Enhancement Preferred**: Minimal, opt-in approach most appropriate

### Recommendation

**✅ MINIMAL ROLE-BASED ENHANCEMENT**: Add optional role preferences for Docker Swarm deployments while maintaining current simple behavior as default.

#### Implementation Plan:
1. **Phase 1**: Add optional `placement.preferred_role` field to services.yaml
2. **Phase 2**: Enhance Swarm generation to include role preferences as soft constraints
3. **Phase 3**: Document role-based deployment patterns for power users

#### Decision Rationale:
- **Appropriate Scale**: Minimal enhancement matches home lab reality
- **User Choice**: Power users can opt-in to role awareness if desired
- **Low Overhead**: Minimal complexity increase
- **Future Compatible**: Foundation for more sophisticated features if needed

**Next Step**: Proceed with Analysis 11.3 to investigate hardware constraint handling.
