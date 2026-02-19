#!/bin/bash
# verify.sh - Build verification with self-healing
# Source this file: source lib/verify.sh

# Also source selfheal if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${SELFHEAL_LOADED:-}" ] && source "$SCRIPT_DIR/selfheal.sh"

# Verify build passes
verify_build() {
    local max_attempts=${1:-3}
    local attempt=0

    # Ensure dependencies first
    ensure_deps || true

    while [ $attempt -lt $max_attempts ]; do
        ((attempt++))

        local output
        local exit_code=0

        if [ -f "package.json" ]; then
            output=$(npm run build 2>&1) || exit_code=$?
        else
            # No package.json, assume success
            return 0
        fi

        if [ $exit_code -eq 0 ]; then
            return 0
        fi

        # Only show errors (saves tokens)
        echo "$output" | grep -E "(error|Error|ERROR|FAIL|failed|Failed|✗|❌)" | head -20

        # Try self-heal
        if try_selfheal "$output"; then
            continue
        fi

        # No self-heal possible, fail
        return 1
    done

    return 1
}

# Verify tests pass
verify_tests() {
    if [ ! -f "package.json" ]; then
        return 0
    fi

    if ! grep -q '"test"' package.json 2>/dev/null; then
        return 0
    fi

    local output
    output=$(npm test 2>&1) || {
        # Only show failed tests (saves tokens)
        echo "$output" | grep -E "(FAIL|failed|Failed|✗|❌|Error)" | head -30
        return 1
    }
    return 0
}

# Full verification (build + tests)
verify_all() {
    verify_build || return 1
    verify_tests || return 1
    return 0
}
