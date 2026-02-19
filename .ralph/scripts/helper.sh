#!/bin/bash
# =============================================================================
# helper.sh - Helper Claude to Unblock Stuck Ralph
#
# This script provides a helper Claude with the ability to:
# - Check Ralph's status (process, logs, stuck duration)
# - Send diagnostic requests to Ralph
# - Analyze stuck situations and suggest actions
# - Verify Ralph is unblocked before exiting
#
# Usage:
#   ~/.ralph/scripts/helper.sh status     # Check Ralph's status
#   ~/.ralph/scripts/helper.sh unblock    # Full unblocking workflow
#   ~/.ralph/scripts/helper.sh ping       # Quick ping
#   ~/.ralph/scripts/helper.sh abort      # Emergency abort
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

RALPH_VM_USER="ralph"
RALPH_VM_HOST="192.168.206.128"
RALPH_PROJECT_DIR="~/projects/nonprofit-matcher"
RALPH_CONTROL_DIR="${HOME}/.ralph/control"
HELPER_MAX_RESPONSE_TIMEOUT=30
HELPER_MAX_STUCK_TIME=3600  # 1 hour
HELPER_MAX_ATTEMPTS=3

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# SSH WRAPPER
# =============================================================================

ralph_ssh() {
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${RALPH_VM_USER}@${RALPH_VM_HOST}" "$@"
}

# =============================================================================
# STATUS CHECKING
# =============================================================================

helper_check_ralph_status() {
    echo -e "${BLUE}=== Checking Ralph Status ===${NC}"

    # Check if Ralph process is running
    local ralph_pid
    ralph_pid=$(ralph_ssh 'pgrep -f "claude --dangerously-skip-permissions" || true')

    if [[ -z "$ralph_pid" ]]; then
        echo -e "${RED}✗ Ralph is not running${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Ralph is running (PID: $ralph_pid)${NC}"

    # Check last output time
    local last_output_time
    local last_output_epoch
    local current_epoch
    local stuck_duration

    last_output_time=$(ralph_ssh "stat -c %y ${RALPH_CONTROL_DIR}/../logs/last_output 2>/dev/null || echo 'never'")
    last_output_epoch=$(ralph_ssh "stat -c %Y ${RALPH_CONTROL_DIR}/../logs/last_output 2>/dev/null || echo 0")
    current_epoch=$(date +%s)
    stuck_duration=$((current_epoch - last_output_epoch))

    echo "Last output: $last_output_time"
    echo "Stuck for: ${stuck_duration}s"

    # Get recent logs
    echo -e "\n${BLUE}=== Recent Ralph Output (last 20 lines) ===${NC}"
    ralph_ssh "tail -20 ${RALPH_CONTROL_DIR}/../logs/current.log 2>/dev/null || echo 'No logs available'"

    # Check for errors
    echo -e "\n${BLUE}=== Recent Errors ===${NC}"
    ralph_ssh "grep -i 'error\\|fail\\|exception' ${RALPH_CONTROL_DIR}/../logs/current.log 2>/dev/null | tail -10 || echo 'No errors found'"

    return 0
}

# =============================================================================
# LOCK ACQUISITION
# =============================================================================

helper_acquire_lock() {
    echo -e "${BLUE}=== Acquiring Helper Lock ===${NC}"

    local lock_result
    lock_result=$(ralph_ssh "
        mkdir -p ${RALPH_CONTROL_DIR}
        if mkdir ${RALPH_CONTROL_DIR}/lock 2>/dev/null; then
            echo 'acquired'
            echo \$\$ > ${RALPH_CONTROL_DIR}/lock/pid
        else
            echo 'locked'
            cat ${RALPH_CONTROL_DIR}/lock/pid 2>/dev/null || echo 'unknown'
        fi
    ")

    if [[ "$lock_result" == "acquired" ]]; then
        echo -e "${GREEN}✓ Lock acquired${NC}"
        return 0
    else
        local locking_pid=$(echo "$lock_result" | tail -1)
        echo -e "${YELLOW}⚠ Lock held by PID: $locking_pid${NC}"
        echo "Another helper session may be active."
        return 1
    fi
}

helper_release_lock() {
    ralph_ssh "rm -rf ${RALPH_CONTROL_DIR}/lock" 2>/dev/null || true
    echo -e "${GREEN}✓ Lock released${NC}"
}

# =============================================================================
# COMMUNICATION
# =============================================================================

helper_send_request() {
    local request_type="$1"
    local payload="$2"

    local request_file="/tmp/helper_request_$$.json"

    cat > "$request_file" << EOF
{
  "version": "1.0",
  "type": "$request_type",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "helper_id": "helper-$(date +%s)-$$",
  "payload": $payload
}
EOF

    ralph_ssh "cat > ${RALPH_CONTROL_DIR}/helper_request.json" < "$request_file"
    rm -f "$request_file"

    echo -e "${GREEN}✓ Sent $request_type request${NC}"
}

helper_wait_response() {
    local timeout="${1:-$HELPER_MAX_RESPONSE_TIMEOUT}"

    echo -e "${BLUE}Waiting for Ralph response (timeout: ${timeout}s)...${NC}"

    for i in $(seq 1 "$timeout"); do
        if ralph_ssh "test -f ${RALPH_CONTROL_DIR}/ralph_response.json"; then
            local response
            response=$(ralph_ssh "cat ${RALPH_CONTROL_DIR}/ralph_response.json")

            # Clear response after reading
            ralph_ssh "rm -f ${RALPH_CONTROL_DIR}/ralph_response.json"

            echo -e "${GREEN}✓ Response received after ${i}s${NC}"
            echo "$response"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}✗ Timeout waiting for response${NC}"
    return 1
}

# =============================================================================
# DIAGNOSTICS
# =============================================================================

helper_diagnose() {
    echo -e "\n${BLUE}=== Running Diagnostics ===${NC}"

    # Send diagnostic request
    helper_send_request "diagnose" '{}'

    # Wait for response
    local response
    response=$(helper_wait_response) || return 1

    # Parse and display
    echo -e "\n${BLUE}=== Diagnostic Results ===${NC}"

    local current_spec
    local current_task
    local stuck_duration
    local last_error
    local checkpoint

    current_spec=$(echo "$response" | jq -r '.payload.current_spec // "unknown"')
    current_task=$(echo "$response" | jq -r '.payload.current_task // "unknown"')
    stuck_duration=$(echo "$response" | jq -r '.payload.stuck_duration // 0')
    last_error=$(echo "$response" | jq -r '.payload.last_error // "none"' | tr -d '\n')
    checkpoint=$(echo "$response" | jq -r '.payload.checkpoint // "unknown"')

    echo "Current Spec: $current_spec"
    echo "Current Task: $current_task"
    echo "Stuck Duration: ${stuck_duration}s"
    echo "Checkpoint: $checkpoint"
    echo "Last Error: $last_error"

    # Export for use in other functions
    export HELPER_DIAG_SPEC="$current_spec"
    export HELPER_DIAG_TASK="$current_task"
    export HELPER_DIAG_STUCK_DURATION="$stuck_duration"
    export HELPER_DIAG_ERROR="$last_error"
    export HELPER_DIAG_CHECKPOINT="$checkpoint"

    return 0
}

# =============================================================================
# ANALYSIS AND SUGGESTIONS
# =============================================================================

helper_analyze_and_suggest() {
    echo -e "\n${BLUE}=== Analyzing Stuck Situation ===${NC}"

    local error="$HELPER_DIAG_ERROR"
    local duration="$HELPER_DIAG_STUCK_DURATION"
    local checkpoint="$HELPER_DIAG_CHECKPOINT"

    local suggestion=""
    local action=""

    # Analyze error patterns
    local error_lower=$(echo "$error" | tr '[:upper:]' '[:lower:]')

    case "$error_lower" in
        *timeout*|*hang*|*no response*)
            suggestion="The current task appears to be timing out. Suggest using mock data to continue."
            action="use_mock"
            ;;
        *api*|*fetch*|*network*|*connection*)
            suggestion="API/Network issue detected. Suggest using mock data to continue development."
            action="use_mock"
            ;;
        *dependen*|*module*|*import*)
            suggestion="Missing dependency detected. Try running: npm install <missing-package>"
            action="manual_review"
            ;;
        *permission*|*access*|*denied*)
            suggestion="Permission issue detected. Check file permissions and try again."
            action="retry"
            ;;
        *syntax*|*parse*|*type*|*compile*)
            suggestion="Compilation error detected. Fix the syntax error before continuing."
            action="manual_review"
            ;;
        *)
            if (( duration > 1800 )); then  # 30 minutes
                suggestion="Stuck for ${duration}s with no clear error. Suggest using mock data to continue."
                action="use_mock"
            else
                suggestion="Unclear issue detected. Manual review recommended."
                action="manual_review"
            fi
            ;;
    esac

    echo "Analysis: $suggestion"
    echo "Suggested Action: $action"

    # Ask for confirmation
    echo -e "\n${YELLOW}Send suggestion to Ralph? (y/n)${NC}"
    read -r confirm

    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        helper_send_suggestion "$action" "$suggestion"
    else
        echo "Suggestion not sent."
    fi
}

helper_send_suggestion() {
    local action="$1"
    local message="$2"

    echo -e "\n${BLUE}=== Sending Suggestion ===${NC}"
    echo "Action: $action"
    echo "Message: $message"

    helper_send_request "suggest" "{\"action\": \"$action\", \"message\": \"$message\"}"

    # Wait for acknowledgment
    local response
    response=$(helper_wait_response) || return 1

    local ack_status
    ack_status=$(echo "$response" | jq -r '.payload.status // "unknown"')

    if [[ "$ack_status" != "error" ]]; then
        echo -e "${GREEN}✓ Ralph acknowledged: $ack_status${NC}"
        return 0
    else
        echo -e "${RED}✗ Ralph returned error${NC}"
        return 1
    fi
}

# =============================================================================
# VERIFICATION
# =============================================================================

helper_verify_unblocked() {
    echo -e "\n${BLUE}=== Verifying Ralph Unblocked ===${NC}"

    echo "Waiting 10 seconds for Ralph to produce output..."
    sleep 10

    local last_output_epoch
    local current_epoch
    local new_stuck_duration

    last_output_epoch=$(ralph_ssh "stat -c %Y ${RALPH_CONTROL_DIR}/../logs/last_output 2>/dev/null || echo 0")
    current_epoch=$(date +%s)
    new_stuck_duration=$((current_epoch - last_output_epoch))

    if (( new_stuck_duration < 15 )); then
        echo -e "${GREEN}✓ Ralph appears unblocked (recent activity detected)${NC}"
        echo "New stuck duration: ${new_stuck_duration}s"

        # Show recent output
        echo -e "\n${BLUE}=== Recent Ralph Output ===${NC}"
        ralph_ssh "tail -10 ${RALPH_CONTROL_DIR}/../logs/current.log"

        return 0
    else
        echo -e "${YELLOW}⚠ Ralph may still be stuck (duration: ${new_stuck_duration}s)${NC}"
        return 1
    fi
}

# =============================================================================
# ESCALATION
# =============================================================================

helper_send_abort() {
    local reason="$1"

    echo -e "\n${RED}=== SENDING ABORT ===${NC}"
    echo "Reason: $reason"

    helper_send_request "abort" "{\"reason\": \"$reason\", \"graceful\": true}"

    echo "Waiting 5 seconds for graceful shutdown..."
    sleep 5

    # Check if still running
    local ralph_pid
    ralph_pid=$(ralph_ssh 'pgrep -f "claude --dangerously-skip-permissions" || true')

    if [[ -n "$ralph_pid" ]]; then
        echo -e "${YELLOW}⚠ Ralph still running, forcing shutdown...${NC}"
        ralph_ssh "pkill -9 -f 'claude --dangerously-skip-permissions'"
        sleep 2
    fi

    echo -e "${RED}✓ Ralph terminated${NC}"
}

helper_escalation_check() {
    local stuck_duration="${1:-0}"
    local attempts="${2:-0}"

    if (( stuck_duration > HELPER_MAX_STUCK_TIME )); then
        echo -e "\n${RED}⚠ CRITICAL: Ralph stuck for ${stuck_duration}s (exceeds ${HELPER_MAX_STUCK_TIME}s threshold)${NC}"
        echo "Recommendation: Abort and restart Ralph"

        echo -e "\n${YELLOW}Abort Ralph? (y/n)${NC}"
        read -r confirm

        if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
            helper_send_abort "stuck_timeout"
            helper_release_lock
            exit 2
        fi

        return 2
    fi

    if (( attempts >= HELPER_MAX_ATTEMPTS )); then
        echo -e "\n${YELLOW}⚠ WARNING: $attempts failed unblock attempts (max: ${HELPER_MAX_ATTEMPTS})${NC}"
        echo "Recommendation: Manual intervention required"
        return 1
    fi

    return 0
}

# =============================================================================
# LOGGING
# =============================================================================

helper_log_session() {
    local outcome="$1"

    local log_dir="${RALPH_CONTROL_DIR}/../logs/helper_sessions"
    local log_file="$log_dir/$(date +%Y%m%d_%H%M%S)_helper_$$.json"

    ralph_ssh "mkdir -p $log_dir"

    local session_data
    session_data=$(cat << EOF
{
  "session_id": "helper-$(date +%s)-$$",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "outcome": "$outcome",
  "diagnostic_data": {
    "current_spec": "$HELPER_DIAG_SPEC",
    "current_task": "$HELPER_DIAG_TASK",
    "stuck_duration": $HELPER_DIAG_STUCK_DURATION,
    "last_error": $(echo "$HELPER_DIAG_ERROR" | jq -Rs .),
    "checkpoint": "$HELPER_DIAG_CHECKPOINT"
  }
}
EOF
)

    echo "$session_data" | ralph_ssh "cat > $log_file"
    echo -e "${GREEN}✓ Session logged to: $log_file${NC}"
}

# =============================================================================
# MAIN WORKFLOW
# =============================================================================

helper_main() {
    local attempt=0

    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Ralph Helper - Unblocking Tool     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"

    # Step 1: Check Ralph status
    if ! helper_check_ralph_status; then
        echo -e "${RED}Cannot proceed - Ralph is not running${NC}"
        exit 1
    fi

    # Step 2: Acquire lock
    if ! helper_acquire_lock; then
        echo -e "${RED}Cannot proceed - another helper is active${NC}"
        exit 1
    fi

    # Ensure lock is released on exit
    trap 'helper_release_lock' EXIT

    # Main loop
    while true; do
        ((attempt++))
        echo -e "\n${BLUE}=== Helper Attempt $attempt ===${NC}"

        # Step 3: Run diagnostics
        if ! helper_diagnose; then
            echo -e "${RED}✗ Diagnostics failed (no response from Ralph)${NC}"

            # Try sending SIGUSR1 to wake up Ralph
            echo -e "${YELLOW}Sending SIGUSR1 to Ralph...${NC}"
            ralph_ssh "pkill -USR1 -f 'claude --dangerously-skip-permissions'" || true
            sleep 2

            # Retry diagnostics
            if ! helper_diagnose; then
                echo -e "${RED}✗ Still no response - Ralph may be completely hung${NC}"
                helper_log_session "no_response"
                exit 1
            fi
        fi

        # Step 4: Check escalation
        helper_escalation_check "$HELPER_DIAG_STUCK_DURATION" "$attempt"
        local escalation_result=$?

        if (( escalation_result == 2 )); then
            # Aborted
            helper_log_session "aborted"
            exit 2
        elif (( escalation_result == 1 )); then
            # Manual intervention needed
            helper_log_session "manual_required"
            echo -e "\n${YELLOW}Manual intervention required. Ralph is waiting.${NC}"
            exit 1
        fi

        # Step 5: Analyze and suggest
        helper_analyze_and_suggest

        # Step 6: Verify unblocked
        if helper_verify_unblocked; then
            echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║     ✓ Ralph Successfully Unblocked!     ║${NC}"
            echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
            helper_log_session "unblocked"
            exit 0
        fi

        # Ask if should try again
        echo -e "\n${YELLOW}Ralph may still be stuck. Try again? (y/n)${NC}"
        read -r retry

        if [[ "$retry" != "y" && "$retry" != "Y" ]]; then
            helper_log_session "user_aborted"
            exit 0
        fi
    done
}

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

case "${1:-help}" in
    status)
        helper_check_ralph_status
        ;;
    diagnose)
        helper_acquire_lock || exit 1
        trap 'helper_release_lock' EXIT
        helper_diagnose
        helper_release_lock
        ;;
    ping)
        helper_acquire_lock || exit 1
        trap 'helper_release_lock' EXIT
        helper_send_request "ping" '{}'
        helper_wait_response
        helper_release_lock
        ;;
    abort)
        helper_acquire_lock || exit 1
        trap 'helper_release_lock' EXIT
        helper_send_abort "manual_abort"
        helper_release_lock
        ;;
    unblock|help|"")
        echo "Usage: $0 {status|diagnose|ping|abort|unblock}"
        echo ""
        echo "Commands:"
        echo "  status    - Check Ralph's current status"
        echo "  diagnose  - Run full diagnostics"
        echo "  ping      - Ping Ralph to check if responsive"
        echo "  abort     - Send abort signal to Ralph"
        echo "  unblock   - Full unblocking workflow (interactive)"
        echo ""

        if [[ "${1:-}" == "unblock" ]]; then
            helper_main
        fi
        ;;
esac
