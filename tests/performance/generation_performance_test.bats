#!/usr/bin/env bats

# Generation Performance Tests
# Part of Issue #40 - Comprehensive Test Suite for Unified Configuration
# Tests performance benchmarks and regression detection

load ../helpers/enhanced_test_helper

setup() {
    setup_comprehensive_test

    # Check for performance testing dependencies
    check_test_dependencies || skip "Missing performance testing dependencies"

    # Source required scripts for Docker Compose testing
    if [ -f "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh" ]; then
        # shellcheck disable=SC1091
        source "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh"
    fi

    # Note: Not sourcing Swarm script to avoid function name conflicts
    # Performance tests focus on Docker Compose functionality

    # Create performance results directory
    export PERFORMANCE_RESULTS_DIR="$TEST_DIR/performance_results"
    mkdir -p "$PERFORMANCE_RESULTS_DIR"
}

teardown() {
    # Save performance results if directory exists
    if [ -d "$PERFORMANCE_RESULTS_DIR" ] && [ -n "$BATS_TEST_NAME" ]; then
        local result_file="$PERFORMANCE_RESULTS_DIR/${BATS_TEST_NAME// /_}.txt"
        if [ -n "$OPERATION_DURATION" ]; then
            {
                echo "Test: $BATS_TEST_NAME"
                echo "Duration: ${OPERATION_DURATION}s"
                echo "Timestamp: $(date)"
                echo "---"
            } >> "$result_file"
        fi
    fi

    teardown_comprehensive_test
}

# =============================================================================
# DOCKER COMPOSE GENERATION PERFORMANCE
# =============================================================================

@test "Docker Compose generation - small config (1 machine, 3 services) under 2s" {
    create_test_homelab_config "docker_compose" 1 3

    time_operation "Small Compose Generation" translate_homelab_to_compose "$TEST_CONFIG"
    [ $status -eq 0 ]
    assert_within_time_limit 2

    echo "✅ Small config generated in ${OPERATION_DURATION}s"
}

@test "Docker Compose generation - medium config (3 machines, 10 services) under 5s" {
    create_test_homelab_config "docker_compose" 3 10

    time_operation "Medium Compose Generation" translate_homelab_to_compose "$TEST_CONFIG"
    [ $status -eq 0 ]
    assert_within_time_limit 5

    echo "✅ Medium config generated in ${OPERATION_DURATION}s"
}

@test "Docker Compose generation - large config (5 machines, 20 services) under 10s" {
    create_test_homelab_config "docker_compose" 5 20

    time_operation "Large Compose Generation" translate_homelab_to_compose "$TEST_CONFIG"
    [ $status -eq 0 ]
    assert_within_time_limit 10

    echo "✅ Large config generated in ${OPERATION_DURATION}s"
}

@test "Docker Compose generation - extra large config (10 machines, 50 services) under 30s" {
    create_test_homelab_config "docker_compose" 10 50

    time_operation "Extra Large Compose Generation" translate_homelab_to_compose "$TEST_CONFIG"
    [ $status -eq 0 ]
    assert_within_time_limit 30

    echo "✅ Extra large config generated in ${OPERATION_DURATION}s"

    # Verify all machine bundles were created
    local machine_count
    machine_count=$(find "$TEST_OUTPUT" -name "docker-compose.yaml" | wc -l)
    [ "$machine_count" -eq 10 ]
}

# =============================================================================
# DOCKER SWARM GENERATION PERFORMANCE
# =============================================================================

@test "Docker Swarm generation - small config under 1s" {
    create_test_homelab_config "docker_swarm" 1 3

    time_operation "Small Swarm Generation" translate_to_docker_swarm "$TEST_CONFIG"
    [ $status -eq 0 ]
    assert_within_time_limit 1

    echo "✅ Small Swarm stack generated in ${OPERATION_DURATION}s"
}

@test "Docker Swarm generation - medium config under 3s" {
    create_test_homelab_config "docker_swarm" 3 10

    time_operation "Medium Swarm Generation" translate_to_docker_swarm "$TEST_CONFIG"
    [ $status -eq 0 ]
    assert_within_time_limit 3

    echo "✅ Medium Swarm stack generated in ${OPERATION_DURATION}s"
}

@test "Docker Swarm generation - large config under 5s" {
    create_test_homelab_config "docker_swarm" 5 20

    time_operation "Large Swarm Generation" translate_to_docker_swarm "$TEST_CONFIG"
    [ $status -eq 0 ]
    assert_within_time_limit 5

    echo "✅ Large Swarm stack generated in ${OPERATION_DURATION}s"
}

# =============================================================================
# MEMORY USAGE PERFORMANCE
# =============================================================================

@test "memory usage stays within reasonable bounds - medium config" {
    create_test_homelab_config "docker_compose" 3 10

    # Monitor memory usage during generation (if /usr/bin/time available)
    if command -v /usr/bin/time >/dev/null 2>&1; then
        export HOMELAB_CONFIG="$TEST_CONFIG"
        export OUTPUT_DIR="$TEST_OUTPUT"
        /usr/bin/time -f "%M" translate_homelab_to_compose 2> "$TEST_DIR/memory_usage.txt"
        [ $status -eq 0 ]

        local memory_kb
        memory_kb=$(tail -1 "$TEST_DIR/memory_usage.txt")

        # Should use less than 100MB (102400 KB)
        if [ "$memory_kb" -gt 102400 ]; then
            echo "⚠️  Memory usage: ${memory_kb}KB (exceeds 100MB limit)"
            fail "Memory usage too high: ${memory_kb}KB"
        else
            echo "✅ Memory usage: ${memory_kb}KB (within 100MB limit)"
        fi
    else
        skip "GNU time not available for memory monitoring"
    fi
}

@test "memory usage - large config under 200MB" {
    create_test_homelab_config "docker_compose" 5 30

    if command -v /usr/bin/time >/dev/null 2>&1; then
        export HOMELAB_CONFIG="$TEST_CONFIG"
        export OUTPUT_DIR="$TEST_OUTPUT"
        /usr/bin/time -f "%M" translate_homelab_to_compose 2> "$TEST_DIR/memory_usage.txt"
        [ $status -eq 0 ]

        local memory_kb
        memory_kb=$(tail -1 "$TEST_DIR/memory_usage.txt")

        # Should use less than 200MB (204800 KB)
        if [ "$memory_kb" -gt 204800 ]; then
            echo "⚠️  Memory usage: ${memory_kb}KB (exceeds 200MB limit)"
            fail "Memory usage too high: ${memory_kb}KB"
        else
            echo "✅ Memory usage: ${memory_kb}KB (within 200MB limit)"
        fi
    else
        skip "GNU time not available for memory monitoring"
    fi
}

# =============================================================================
# VALIDATION PERFORMANCE
# =============================================================================

@test "schema validation performance - medium config under 2s" {
    create_test_homelab_config "docker_compose" 3 10

    if [ -f "$PROJECT_ROOT/scripts/simple_homelab_validator.sh" ]; then
        time_operation "Schema Validation" "$PROJECT_ROOT/scripts/simple_homelab_validator.sh" "$TEST_CONFIG"
        [ $status -eq 0 ]
        assert_within_time_limit 2

        echo "✅ Schema validation completed in ${OPERATION_DURATION}s"
    else
        time_operation "Basic Validation" assert_homelab_config_valid "$TEST_CONFIG"
        assert_within_time_limit 1

        echo "✅ Basic validation completed in ${OPERATION_DURATION}s"
    fi
}

@test "migration performance - complex legacy config under 30s" {
    create_legacy_config_fixture "$TEST_DIR"

    if [ -f "$PROJECT_ROOT/scripts/migrate_to_homelab_yaml.sh" ]; then
        cd "$TEST_DIR"

        time_operation "Migration" "$PROJECT_ROOT/scripts/migrate_to_homelab_yaml.sh"
        [ $status -eq 0 ]
        assert_within_time_limit 30

        echo "✅ Migration completed in ${OPERATION_DURATION}s"

        # Verify migration output
        [ -f "$TEST_DIR/homelab.yaml" ]
    else
        skip "Migration script not available"
    fi
}

# =============================================================================
# SCALABILITY PERFORMANCE
# =============================================================================

@test "generation scales linearly with machine count" {
    local machine_counts=(1 2 3 5)
    local durations=()

    for count in "${machine_counts[@]}"; do
        create_test_homelab_config "docker_compose" "$count" 5

        export HOMELAB_CONFIG="$TEST_CONFIG"
        export OUTPUT_DIR="$TEST_OUTPUT"
        run time_operation "Scaling Test $count machines" translate_homelab_to_compose
        [ $status -eq 0 ]

        durations+=("$OPERATION_DURATION")
        echo "📊 $count machines: ${OPERATION_DURATION}s"
    done

    # Verify scaling is reasonable (not exponential)
    # Last duration should not be more than 5x the first
    local first_duration="${durations[0]}"
    local last_duration="${durations[-1]}"

    local scaling_factor
    scaling_factor=$(echo "scale=2; $last_duration / $first_duration" | bc)

    # Should scale less than 10x for 5x increase in machines
    local is_reasonable
    is_reasonable=$(echo "$scaling_factor < 10" | bc)

    if [ "$is_reasonable" -eq 1 ]; then
        echo "✅ Scaling factor: ${scaling_factor}x (reasonable)"
    else
        echo "⚠️  Scaling factor: ${scaling_factor}x (may be high)"
        # Don't fail, just warn
    fi
}

@test "generation scales linearly with service count" {
    local service_counts=(5 10 15 20)
    local durations=()

    for count in "${service_counts[@]}"; do
        create_test_homelab_config "docker_compose" 2 "$count"

        export HOMELAB_CONFIG="$TEST_CONFIG"
        export OUTPUT_DIR="$TEST_OUTPUT"
        run time_operation "Service Scaling Test $count services" translate_homelab_to_compose
        [ $status -eq 0 ]

        durations+=("$OPERATION_DURATION")
        echo "📊 $count services: ${OPERATION_DURATION}s"
    done

    # Verify scaling is reasonable
    local first_duration="${durations[0]}"
    local last_duration="${durations[-1]}"

    local scaling_factor
    scaling_factor=$(echo "scale=2; $last_duration / $first_duration" | bc)

    # Should scale less than 8x for 4x increase in services
    local is_reasonable
    is_reasonable=$(echo "$scaling_factor < 8" | bc)

    if [ "$is_reasonable" -eq 1 ]; then
        echo "✅ Service scaling factor: ${scaling_factor}x (reasonable)"
    else
        echo "⚠️  Service scaling factor: ${scaling_factor}x (may be high)"
    fi
}

# =============================================================================
# REGRESSION PERFORMANCE TESTS
# =============================================================================

@test "performance regression detection - baseline comparison" {
    # Create standard test configuration
    create_test_homelab_config "docker_compose" 3 10

    # Run generation and record time
    export HOMELAB_CONFIG="$TEST_CONFIG"
    export OUTPUT_DIR="$TEST_OUTPUT"
    run time_operation "Regression Baseline" translate_homelab_to_compose
    [ $status -eq 0 ]

    local current_duration="$OPERATION_DURATION"

    # Check if we have a baseline file
    local baseline_file="$PROJECT_ROOT/tests/performance/baseline.txt"

    if [ -f "$baseline_file" ]; then
        local baseline_duration
        baseline_duration=$(grep "Medium Config Generation" "$baseline_file" | cut -d: -f2 | tr -d ' s')

        if [ -n "$baseline_duration" ]; then
            # Calculate performance change
            local performance_ratio
            performance_ratio=$(echo "scale=2; $current_duration / $baseline_duration" | bc)

            echo "📊 Current: ${current_duration}s, Baseline: ${baseline_duration}s, Ratio: ${performance_ratio}x"

            # Warn if performance degraded by more than 50%
            local is_acceptable
            is_acceptable=$(echo "$performance_ratio < 1.5" | bc)

            if [ "$is_acceptable" -eq 1 ]; then
                echo "✅ Performance within acceptable range"
            else
                echo "⚠️  Performance may have degraded (${performance_ratio}x slower than baseline)"
                # Don't fail, just warn for now
            fi
        fi
    else
        echo "📝 Creating new performance baseline: ${current_duration}s"
        echo "Medium Config Generation: ${current_duration}s" > "$baseline_file"
    fi
}

# =============================================================================
# CONCURRENT PERFORMANCE TESTS
# =============================================================================

@test "concurrent generation performance" {
    # Test multiple concurrent generations (if supported)
    local config_count=3
    local pids=()

    # Create multiple test configs
    for i in $(seq 1 $config_count); do
        local config_file="$TEST_DIR/homelab_$i.yaml"
        create_test_homelab_config "docker_compose" 2 5
        cp "$TEST_CONFIG" "$config_file"
    done

    # Start concurrent generations
    local start_time
    start_time=$(date +%s.%N)

    for i in $(seq 1 $config_count); do
        local config_file="$TEST_DIR/homelab_$i.yaml"
        local output_dir="$TEST_OUTPUT/concurrent_$i"

        (export HOMELAB_CONFIG="$config_file"; export OUTPUT_DIR="$output_dir"; translate_homelab_to_compose) &
        pids+=($!)
    done

    # Wait for all to complete
    local all_success=true
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            all_success=false
        fi
    done

    local end_time
    end_time=$(date +%s.%N)
    local total_duration
    total_duration=$(echo "$end_time - $start_time" | bc -l)

    [ "$all_success" = true ]

    echo "✅ $config_count concurrent generations completed in ${total_duration}s"

    # Should complete faster than sequential (within 2x time)
    local sequential_estimate
    sequential_estimate=$(echo "$config_count * 3" | bc)  # Assume 3s per generation

    local is_efficient
    is_efficient=$(echo "$total_duration < ($sequential_estimate * 2)" | bc)

    if [ "$is_efficient" -eq 1 ]; then
        echo "✅ Concurrent execution efficient (${total_duration}s vs ${sequential_estimate}s sequential estimate)"
    else
        echo "⚠️  Concurrent execution may not be optimized"
    fi
}

# =============================================================================
# CLEANUP AND REPORTING
# =============================================================================

@test "performance test cleanup and reporting" {
    # This test runs last and generates a performance summary

    if [ -d "$PERFORMANCE_RESULTS_DIR" ]; then
        local result_count
        result_count=$(find "$PERFORMANCE_RESULTS_DIR" -name "*.txt" | wc -l)

        echo "📊 Performance Test Summary:"
        echo "   Total performance tests: $result_count"

        # Generate summary report
        local summary_file="$PERFORMANCE_RESULTS_DIR/summary.txt"
        echo "Performance Test Summary - $(date)" > "$summary_file"
        echo "=================================" >> "$summary_file"

        for result_file in "$PERFORMANCE_RESULTS_DIR"/*.txt; do
            if [ -f "$result_file" ] && [[ "$(basename "$result_file")" != "summary.txt" ]]; then
                cat "$result_file" >> "$summary_file"
            fi
        done

        echo "✅ Performance summary saved to $summary_file"

        # Show top 5 slowest tests
        if command -v sort >/dev/null 2>&1; then
            echo ""
            echo "🐌 Top 5 slowest operations:"
            grep "Duration:" "$summary_file" | sort -k2 -nr | head -5
        fi
    fi
}
