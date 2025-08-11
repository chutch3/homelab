# TDD Implementation Plan

**Instructions:** Find the next unmarked test (❌), implement it, make it pass, mark complete (✅), commit.

## Issue #21: machines.yml Investigation

✅ **Analysis 1.1**: `analyze_machines_yml_usage` - Count actual usage vs references (COMPLETED)
✅ **Analysis 1.2**: `compare_swarm_vs_machines` - Compare approaches (COMPLETED)
✅ **Analysis 1.3**: `validate_machines_value` - Validate unique value (COMPLETED)

**Context**: Check if `machines.yml.example` and `scripts/machines.sh` are actually needed.

## Issue #22: services.yaml Configuration Concerns

✅ **Analysis 2.1**: `analyze_service_enablement` - Enhanced analysis with new architecture context
✅ **Analysis 2.2**: `analyze_service_config_consistency` - Validate single source of truth
✅ **Analysis 2.3**: `analyze_service_schema_validation` - Ensure consistent schema

**Context**: Ensure consistent usage of `config/services.yaml` as single source of truth.

## Issue #23: artifact_copier Implementation

❌ **Test 3.1**: `test_artifact_copier_basic_copy` - Copy single file via SSH
❌ **Test 3.2**: `test_artifact_copier_multiple_machines` - Copy to machine list
❌ **Test 3.3**: `test_artifact_copier_skip_driver` - Skip current machine
❌ **Test 3.4**: `test_artifact_copier_dry_run` - Preview operations
❌ **Test 3.5**: `test_artifact_copier_error_handling` - Handle failures

**Context**: Create new component to distribute generated files across machines.

## Issue #24: Generation Process

❌ **Test 4.1**: `test_unified_generation_interface` - Single command for all artifacts
❌ **Test 4.2**: `test_generation_idempotent` - Reproducible results
❌ **Test 4.3**: `test_generation_with_validation` - Include validation step
❌ **Test 4.4**: `test_incremental_generation` - Only regenerate changed artifacts

**Context**: Unify scattered logic in `scripts/service_generator.sh`.

## Issue #25: Driver Node Architecture

❌ **Test 5.1**: `test_driver_node_identification` - Identify current machine
❌ **Test 5.2**: `test_driver_node_skip_logic` - Skip in copy operations
❌ **Test 5.3**: `test_driver_node_artifact_validation` - Ensure artifacts exist

**Context**: Clarify why driver nodes are skipped in artifact copying.

## Issue #26: Machine/Service Relationship

❌ **Test 6.1**: `test_service_placement_constraints` - Service to machine mapping
❌ **Test 6.2**: `test_config_separation` - No config duplication
❌ **Test 6.3**: `test_placement_rules_validation` - Validate placement logic

**Context**: Define how machines and services relate in configuration.

## Issue #27: Artifact Validation

❌ **Test 7.1**: `test_docker_compose_validation` - Validate YAML syntax
❌ **Test 7.2**: `test_nginx_config_validation` - Validate nginx syntax
❌ **Test 7.3**: `test_environment_validation` - Check required env vars
❌ **Test 7.4**: `test_artifact_consistency` - Cross-artifact consistency

**Context**: Validate generated files before distribution.

## Issue #28: Integration

❌ **Test 8.1**: `test_complete_single_machine` - End-to-end single node
❌ **Test 8.2**: `test_complete_multi_machine` - End-to-end multi-node
❌ **Test 8.3**: `test_error_recovery` - Handle failures gracefully
❌ **Test 8.4**: `test_performance` - Reasonable completion time

**Context**: Validate complete workflow after all components implemented.

## Issue #29: Application vs Service Configuration

✅ **Analysis 9.1**: `analyze_config_relationships` - Define app vs service config distinction
✅ **Analysis 9.2**: `validate_config_boundaries` - Ensure clear separation of concerns
✅ **Analysis 9.3**: `design_unified_approach` - Determine if merger is needed

**Context**: Clarify relationship between application configs and service configurations.

## Issue #30: Generation Engine Clarity

✅ **Analysis 10.1**: `map_generation_inputs` - Document all input sources and processing
✅ **Analysis 10.2**: `define_transformation_rules` - Clarify processing logic
✅ **Analysis 10.3**: `create_flow_diagrams` - Visualize data transformation

**Context**: Clarify generation engine inputs, outputs, and processing logic.

## Issue #31: Node-Specific Generation

❌ **Test 11.1**: `test_node_capability_detection` - Identify node-specific needs
❌ **Test 11.2**: `test_role_based_filtering` - Filter services by node role
❌ **Test 11.3**: `test_hardware_constraints` - Respect node hardware limits

**Context**: Implement node-specific artifact generation and deployment logic.

## Issue #32: Configuration Orchestration

❌ **Analysis 12.1**: `map_config_dependencies` - Identify all configuration relationships
❌ **Test 12.2**: `test_dependency_resolution` - Implement dependency ordering
❌ **Test 12.3**: `test_circular_dependency_detection` - Prevent circular deps

**Context**: Design configuration orchestration and dependency management.

---

**Testing Framework**: Use BATS in `tests/unit/scripts/` following existing patterns.
**Key Files**: `scripts/service_generator.sh`, `scripts/machines.sh`, `config/services.yaml`
