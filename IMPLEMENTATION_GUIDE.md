# Implementation Guide for Agents

This guide explains how to implement the architecture issues independently using TDD methodology.

## 🎯 Quick Start for Agents

1. **Read the plan**: Check `plan.md` for the next unmarked test (❌)
2. **Understand context**: Read the corresponding GitHub issue for full context
3. **Follow TDD cycle**: Red → Green → Refactor
4. **Mark progress**: Update `plan.md` with ✅ when test is complete
5. **Commit properly**: Use conventional commits as specified

## 📋 TDD Process

### Red Phase (Write Failing Test)
1. Create test file in `tests/unit/scripts/` following existing patterns
2. Use BATS framework like other tests in the codebase
3. Include `test_helper.bash` for common utilities
4. Write test that defines the expected behavior
5. Run test to confirm it fails: `bats tests/unit/scripts/your_test.bats`

### Green Phase (Make Test Pass)
1. Implement minimum code needed to make test pass
2. Create new files in `scripts/` or enhance existing ones
3. Focus on making the test pass, not perfect code
4. Run test again to confirm it passes

### Refactor Phase (Improve Code)
1. Clean up code while keeping tests green
2. Remove duplication, improve naming, etc.
3. Run all tests to ensure nothing breaks
4. Commit when stable

## 🗂️ File Structure Reference

```
scripts/
├── common.sh              # Common utilities
├── machines.sh            # Machine management (existing)
├── service_generator.sh   # Generation logic (existing)
├── ssh.sh                 # SSH utilities (existing)
└── artifact_copier.sh     # New - to be created

tests/unit/scripts/
├── test_helper.bash       # Common test utilities
├── machines_test.bats     # Machine tests (existing)
└── artifact_copier_test.bats  # New - to be created

config/
├── services.yaml          # Service definitions (existing)
└── volumes.yaml           # Volume definitions (existing)

machines.yml.example       # Machine configuration example
```

## 🧪 Testing Patterns

### Basic Test Structure
```bash
#!/usr/bin/env bats

load test_helper

@test "descriptive test name" {
    # Setup
    setup_test_environment

    # Execute
    run your_function_under_test

    # Assert
    assert_success
    assert_output --partial "expected output"
}
```

### Common Test Utilities
- `setup_test_environment` - Clean test setup
- `teardown_test_environment` - Clean test teardown
- `assert_success` - Verify command succeeded
- `assert_failure` - Verify command failed
- `assert_output` - Check command output
- `assert_line` - Check specific output line

## 🔍 Key Implementation Areas

### Issue #21: machines.yml Investigation
**Goal**: Determine if machines.yml is actually needed
**Files**: `machines.yml.example`, `scripts/machines.sh`
**Tests**: Analyze usage patterns and alternatives

### Issue #22: service.yml Concerns
**Goal**: Resolve naming confusion with services.yaml
**Files**: `config/services.yaml`
**Tests**: Audit references and ensure consistency

### Issue #23: artifact_copier
**Goal**: Create component to copy files to multiple machines
**Files**: New `scripts/artifact_copier.sh`
**Tests**: File copying, SSH handling, error recovery

### Issue #24: Generation Process
**Goal**: Unify scattered generation logic
**Files**: `scripts/service_generator.sh`
**Tests**: Unified interface, validation, reproducibility

### Issue #25: Driver Node Logic
**Goal**: Clarify driver node behavior in copying
**Files**: Integration with artifact_copier
**Tests**: Node identification, skip logic

### Issue #26: Config Relationships
**Goal**: Define how machines and services relate
**Files**: Both machine and service configs
**Tests**: Placement logic, constraint validation

### Issue #27: Artifact Validation
**Goal**: Validate generated files before deployment
**Files**: Validation utilities
**Tests**: YAML validation, nginx validation, consistency

### Issue #28: Integration
**Goal**: End-to-end workflow validation
**Files**: All components together
**Tests**: Complete workflows, error handling

## 📝 Commit Message Format

Follow conventional commits:
- `test: add validation for artifact copier basic functionality`
- `feat: implement basic file copying in artifact_copier`
- `refactor: simplify error handling in artifact_copier`
- `docs: update machines.yml usage documentation`

## 🤝 Working with Existing Code

### Understanding Current System
1. The system uses `config/services.yaml` as single source of truth
2. `scripts/service_generator.sh` contains generation logic
3. Tests use BATS framework with established patterns
4. SSH functionality exists in `scripts/ssh.sh`

### Integration Points
- Use existing SSH utilities rather than recreating
- Follow existing test patterns and naming
- Integrate with current CLI interface in `selfhosted.sh`
- Respect existing configuration schemas

## ⚠️ Important Notes

- **Each issue is independent** - can be worked on separately
- **Tests come first** - always write failing test before implementation
- **Minimal implementation** - just enough to make tests pass
- **Follow existing patterns** - don't reinvent established approaches
- **Update plan.md** - mark tests complete as you finish them

## 🔄 Getting Started

1. Pick any unmarked test from `plan.md`
2. Read the corresponding GitHub issue for context
3. Examine the relevant existing files
4. Write the failing test
5. Implement minimal code to pass
6. Refactor and commit
7. Move to next test

Each issue builds toward a complete multi-machine deployment system following the architecture diagram requirements.
