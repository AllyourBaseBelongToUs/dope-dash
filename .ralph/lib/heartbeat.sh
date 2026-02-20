#!/bin/bash
# =============================================================================
# heartbeat.sh - Heartbeat tracking for Ralph execution
#
# Updates the project heartbeat file that the watchdog monitors.
# The watchdog checks file modification time to detect if Ralph is alive.
#
# Usage:
#   source "$LIB_DIR/heartbeat.sh"
#   heartbeat_update "status_message"
#
# The heartbeat file is at: .ralph/heartbeat.json
# Watchdog monitors: ~/projects/nonprofit-matcher/.ralph/heartbeat.json
# =============================================================================

set -euo pipefail

# Heartbeat file location (project-specific)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RALPH_HEARTBEAT_FILE="${PROJECT_DIR}/.ralph/heartbeat.json"

# Ensure heartbeat directory exists
mkdir -p "$(dirname "$RALPH_HEARTBEAT_FILE")"

# =============================================================================
# MAIN HEARTBEAT FUNCTION
# =============================================================================

heartbeat_update() {
    local status="${1:-alive}"
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Update heartbeat file with current timestamp and status
    echo "{\"timestamp\": \"$timestamp\", \"status\": \"$status\"}" > "$RALPH_HEARTBEAT_FILE"

    # For debugging: log heartbeat updates (optional, can be enabled)
    # echo "[$(date +%H:%M:%S)] Heartbeat: $status" >&2
}

# =============================================================================
# CONVENIENCE FUNCTIONS FOR COMMON STATUS MESSAGES
# =============================================================================

heartbeat_starting() {
    heartbeat_update "starting"
}

heartbeat_running() {
    heartbeat_update "running"
}

heartbeat_spec_start() {
    local spec_name="${1:-unknown}"
    heartbeat_update "spec_start:${spec_name}"
}

heartbeat_spec_done() {
    local spec_name="${1:-unknown}"
    heartbeat_update "spec_done:${spec_name}"
}

heartbeat_spec_failed() {
    local spec_name="${1:-unknown}"
    heartbeat_update "spec_failed:${spec_name}"
}

heartbeat_building() {
    heartbeat_update "building"
}

heartbeat_testing() {
    heartbeat_update "testing"
}

heartbeat_complete() {
    heartbeat_update "complete"
}

heartbeat_error() {
    local error="${1:-unknown}"
    heartbeat_update "error:${error}"
}

# =============================================================================
# INITIALIZATION - Create initial heartbeat if missing
# =============================================================================

heartbeat_init() {
    if [[ ! -f "$RALPH_HEARTBEAT_FILE" ]]; then
        heartbeat_update "initialized"
    fi
}

# Auto-initialize when sourced
heartbeat_init
