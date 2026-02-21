#!/bin/bash
# =============================================================================
# ralph-helper.sh - Ralph-side implementation for helper Claude communication
#
# This script provides Ralph with the ability to:
# - Receive helper requests via JSON files
# - Respond with diagnostic information
# - Execute suggested actions (use_mock, retry, manual_review)
# - Handle graceful abort requests
#
# Usage (source in ralph.sh):
#   source ~/.ralph/scripts/ralph-helper.sh
#   _ralph_helper_init
#
# Then call checkpoints:
#   _ralph_check_helper_checkpoint "before_spec" "01-project-setup.md"
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# Directories
RALPH_CONTROL_DIR="${HOME}/.ralph/control"
RALPH_LOG_DIR="${HOME}/.ralph/logs"
RALPH_HELPER_REQUEST="${RALPH_CONTROL_DIR}/helper_request.json"
RALPH_HELPER_RESPONSE="${RALPH_CONTROL_DIR}/ralph_response.json"

# Ensure directories exist
mkdir -p "$RALPH_CONTROL_DIR" "$RALPH_LOG_DIR"/{helper_sessions,stuck_incidents}

# Track last output time for stuck detection
RALPH_LAST_OUTPUT_FILE="${RALPH_LOG_DIR}/last_output"

# =============================================================================
# HELPER CHECKPOINT - Called throughout Ralph's execution
# =============================================================================

_ralph_check_helper_checkpoint() {
    local checkpoint_name="${1:-unknown}"
    local context="${2:-}"

    # Update last output time
    date +%s > "$RALPH_LAST_OUTPUT_FILE"

    # Check if helper request exists
    if [[ -f "$RALPH_HELPER_REQUEST" ]]; then
        _ralph_process_helper_request "$checkpoint_name" "$context"
    fi
}

# =============================================================================
# PROCESS HELPER REQUEST
# =============================================================================

_ralph_process_helper_request() {
    local checkpoint_name="$1"
    local context="$2"

    # Read and parse request
    if ! command -v jq &> /dev/null; then
        echo "[Ralph:Helper] jq not available, cannot process helper request" >&2
        return 1
    fi

    local request_type
    local helper_id
    local timestamp

    request_type=$(jq -r '.type // "unknown"' "$RALPH_HELPER_REQUEST" 2>/dev/null)
    helper_id=$(jq -r '.helper_id // "unknown"' "$RALPH_HELPER_REQUEST" 2>/dev/null)
    timestamp=$(jq -r '.timestamp // "unknown"' "$RALPH_HELPER_REQUEST" 2>/dev/null)

    echo "[Ralph:Helper] Received request: type=$request_type from=$helper_id at=$timestamp" >&2

    # Build response based on request type
    case "$request_type" in
        ping)
            _ralph_respond_pong
            ;;
        diagnose|status)
            _ralph_respond_status "$checkpoint_name" "$context"
            ;;
        suggest)
            _ralph_handle_suggestion "$checkpoint_name" "$context"
            ;;
        abort)
            _ralph_handle_abort
            ;;
        *)
            _ralph_respond_error "Unknown request type: $request_type"
            ;;
    esac

    # Remove request (consume it)
    rm -f "$RALPH_HELPER_REQUEST"

    # Log interaction
    _ralph_log_helper_interaction "$request_type" "$helper_id"
}

# =============================================================================
# RESPONSE BUILDERS
# =============================================================================

_ralph_respond_pong() {
    cat > "$RALPH_HELPER_RESPONSE" << EOF
{
  "version": "1.0",
  "type": "pong",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "payload": {
    "status": "alive",
    "uptime_seconds": "$(($(date +%s) - RALPH_START_TIME))"
  }
}
EOF
}

_ralph_respond_status() {
    local checkpoint_name="$1"
    local context="$2"

    # Gather diagnostic info
    local current_spec="${RALPH_CURRENT_SPEC:-unknown}"
    local current_task="${RALPH_CURRENT_TASK:-unknown}"
    local last_output="$(tail -1 "$RALPH_LOG_DIR/current.log" 2>/dev/null || echo 'no logs')"
    local last_error="$(grep -i "error\|fail\|exception" "$RALPH_LOG_DIR/current.log" 2>/dev/null | tail -1 || echo 'none')"
    local stuck_since="$(stat -c %Y "$RALPH_LAST_OUTPUT_FILE" 2>/dev/null || echo 0)"
    local stuck_duration="$(($(date +%s) - stuck_since))"

    # Get memory info
    local memory_mb="unknown"
    if command -v free &> /dev/null; then
        memory_mb=$(free -m | awk '/^Mem:/{print $3}')
    fi

    # Get active files (if lsof available)
    local active_files="[]"
    if command -v lsof &> /dev/null; then
        active_files=$(
            lsof -p $$ 2>/dev/null | \
            grep -oE '/home/ralph/projects/nonprofit-matcher/[^ ]+' | \
            sort -u | head -10 | \
            jq -R '.' | jq -s -c 'map(select(length > 0))'
        ) || active_files="[]"
    fi

    cat > "$RALPH_HELPER_RESPONSE" << EOF
{
  "version": "1.0",
  "type": "status_update",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "payload": {
    "current_spec": "$current_spec",
    "current_task": "$current_task",
    "stuck_since": "$(date -u -d @$stuck_since +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')",
    "stuck_duration": $stuck_duration,
    "last_output": $(echo "$last_output" | jq -Rs .),
    "last_error": $(echo "$last_error" | jq -Rs .),
    "memory_mb": $memory_mb,
    "active_files": $active_files,
    "checkpoint": "$checkpoint_name",
    "context": "$context",
    "environment": "${RALPH_ENV:-dev}"
  }
}
EOF
}

_ralph_handle_suggestion() {
    local checkpoint_name="$1"
    local context="$2"

    local action
    local message
    local suggestion_code

    action=$(jq -r '.payload.action // "unknown"' "$RALPH_HELPER_REQUEST")
    message=$(jq -r '.payload.message // ""' "$RALPH_HELPER_REQUEST")
    suggestion_code=$(jq -r '.payload.suggestion_code // ""' "$RALPH_HELPER_REQUEST")

    echo "[Ralph:Helper] Received suggestion: action=$action" >&2
    echo "[Ralph:Helper] Message: $message" >&2

    # Execute suggested action
    case "$action" in
        use_mock)
            echo "[Ralph:Helper] Using mock data for API calls..." >&2
            export RALPH_USE_MOCK_DATA=true
            _ralph_respond_acknowledge "using_mock_data"
            ;;
        retry)
            echo "[Ralph:Helper] Retrying current operation..." >&2
            _ralph_respond_acknowledge "retrying"
            ;;
        manual_review)
            echo "[Ralph:Helper] Awaiting manual review..." >&2
            _ralph_respond_acknowledge "awaiting_manual_review"
            ;;
        *)
            _ralph_respond_error "Unknown action: $action"
            return 1
            ;;
    esac
}

_ralph_handle_abort() {
    local reason
    reason=$(jq -r '.payload.reason // "unknown"' "$RALPH_HELPER_REQUEST")

    echo "[Ralph:Helper] Received abort request: reason=$reason" >&2
    echo "[Ralph:Helper] Shutting down gracefully..." >&2

    cat > "$RALPH_HELPER_RESPONSE" << EOF
{
  "version": "1.0",
  "type": "acknowledge",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "payload": {
    "status": "aborting",
    "reason": "$reason"
  }
}
EOF

    # Give helper time to read response
    sleep 1

    # Exit Ralph
    exit 0
}

_ralph_respond_acknowledge() {
    local status="$1"

    cat > "$RALPH_HELPER_RESPONSE" << EOF
{
  "version": "1.0",
  "type": "acknowledge",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "payload": {
    "status": "$status"
  }
}
EOF
}

_ralph_respond_error() {
    local error_message="$1"

    cat > "$RALPH_HELPER_RESPONSE" << EOF
{
  "version": "1.0",
  "type": "error",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "payload": {
    "error": "$error_message"
  }
}
EOF
}

# =============================================================================
# LOGGING
# =============================================================================

_ralph_log_helper_interaction() {
    local request_type="$1"
    local helper_id="$2"
    local log_file="${RALPH_LOG_DIR}/helper_sessions/$(date +%Y%m%d_%H%M%S)_interaction_${helper_id}.log"

    {
        echo "=== RALPH HELPER INTERACTION ==="
        echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "Request Type: $request_type"
        echo "Helper ID: $helper_id"
        echo "Current Spec: ${RALPH_CURRENT_SPEC:-unknown}"
        echo "Current Task: ${RALPH_CURRENT_TASK:-unknown}"
    } > "$log_file"
}

# =============================================================================
# WATCHDOG - Detects when Ralph is stuck
# =============================================================================

_ralph_watchdog_start() {
    local check_interval=300  # Check every 5 minutes
    local stuck_threshold=600  # Consider stuck after 10 minutes of no output

    (
        while true; do
            sleep "$check_interval"

            local last_output_time
            last_output_time=$(cat "$RALPH_LAST_OUTPUT_FILE" 2>/dev/null || echo 0)
            local current_time=$(date +%s)
            local time_since_output=$((current_time - last_output_time))

            if (( time_since_output > stuck_threshold )); then
                echo "[Ralph:Watchdog] ALERT: No output for ${time_since_output}s - possible stuck!" >&2

                # Log stuck incident
                local stuck_log="${RALPH_LOG_DIR}/stuck_incidents/$(date +%Y%m%d_%H%M%S)_stuck.json"
                cat > "$stuck_log" << EOF
{
  "detected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "stuck_duration_seconds": $time_since_output,
  "current_spec": "${RALPH_CURRENT_SPEC:-unknown}",
  "current_task": "${RALPH_CURRENT_TASK:-unknown}",
  "last_output": "$(tail -1 "$RALPH_LOG_DIR/current.log" 2>/dev/null || echo 'none')",
  "helper_notified": false
}
EOF

                # Run stuck hook if exists
                if [[ -f "${HOME}/.ralph/hooks/on_stuck.sh" ]]; then
                    bash "${HOME}/.ralph/hooks/on_stuck.sh" "$stuck_log"
                fi
            fi
        done
    ) &

    echo $! > "${RALPH_LOG_DIR}/watchdog.pid"
}

# =============================================================================
# SIGNAL HANDLER - Immediate helper check on SIGUSR1
# =============================================================================

_ralph_helper_signal_handler() {
    echo "[Ralph:Helper] Received SIGUSR1 - checking for helper requests..." >&2
    _ralph_check_helper_checkpoint "signal" "SIGUSR1"
}

# Install signal handler
trap '_ralph_helper_signal_handler' USR1

# =============================================================================
# INITIALIZATION
# =============================================================================

_ralph_helper_init() {
    export RALPH_START_TIME=$(date +%s)
    date +%s > "$RALPH_LAST_OUTPUT_FILE"
    _ralph_watchdog_start
    echo "[Ralph:Helper] Helper protocol initialized. Send SIGUSR1 for immediate check." >&2
    echo "[Ralph:Helper] Control directory: $RALPH_CONTROL_DIR" >&2
}

# Auto-initialize if script is sourced
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    _ralph_helper_init
fi
