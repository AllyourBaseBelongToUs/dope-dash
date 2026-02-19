#!/bin/bash
# =============================================================================
# watchdog-mini.sh - Lightweight watchdog with mini Claude spawn
#
# This script runs in cron on the VM
# When heartbeat stale: Spawns mini Claude -> kicks Ralph's ass -> exits
#
# Location: ~/watchdog-control/watchdog-mini.sh (OUTSIDE project directory)
# Usage:
#   watchdog-mini.sh [--daemon] [INTERVAL_MINUTES] [RUNS]
#   watchdog-mini.sh --loop [INTERVAL_MINUTES] [RUNS]
#
# Examples:
#   watchdog-mini.sh 15 20    # Run every 15 min, 20 times (5 hours)
#   watchdog-mini.sh 5 12     # Run every 5 min, 12 times (1 hour)
# =============================================================================

set -euo pipefail

# Configuration
WATCHDOG_DIR="$HOME/watchdog-control"
PROJECT_DIR="$HOME/projects/dope-dash"
HEARTBEAT_FILE="$PROJECT_DIR/.ralph/heartbeat.json"
LOG_FILE="$PROJECT_DIR/.ralph/logs/watchdog-mini.log"
MINI_SKILL="$HOME/.claude/skills/watchdog-mini.md"
STALE_MINUTES=20
PID_FILE="$WATCHDOG_DIR/watchdog.pid"

# Default values
DEFAULT_INTERVAL_MINUTES=15
DEFAULT_MAX_RUNS=20

# =============================================================================
# DAEMON MODE (for background execution)
# =============================================================================

# Check if already running
check_already_running() {
    if [[ -f "$PID_FILE" ]]; then
        local old_pid
        old_pid=$(cat "$PID_FILE")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            echo "Watchdog already running (PID: $old_pid)"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi
}

# Daemon mode: fork into background properly
run_as_daemon() {
    local interval_minutes="${1:-$DEFAULT_INTERVAL_MINUTES}"
    local max_runs="${2:-$DEFAULT_MAX_RUNS}"

    check_already_running

    # Get the script directory
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Fork into background using nohup (reliable daemon approach)
    nohup bash "$script_dir/watchdog-mini.sh" --loop "$interval_minutes" "$max_runs" </dev/null >/dev/null 2>&1 &

    # Wait a moment for the child to start and write its PID
    sleep 0.5

    # Check if PID file was created
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        echo "Watchdog mini started (PID: $pid, ${max_runs} runs × ${interval_minutes}min = $((max_runs * interval_minutes / 60))h total)"
        exit 0
    else
        echo "Failed to start watchdog"
        exit 1
    fi
}

# Save PID on startup
save_pid() {
    echo $$ > "$PID_FILE"
}

# Cleanup PID on exit
cleanup_pid() {
    rm -f "$PID_FILE"
}

# =============================================================================
# LOGGING
# =============================================================================

# Ensure directories exist
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# CHECK HEARTBEAT FILE
# =============================================================================

check_heartbeat() {
    if [[ ! -f "$HEARTBEAT_FILE" ]]; then
        echo ""
        return 0
    fi

    # Get file modification time
    if stat -c %Y "$HEARTBEAT_FILE" >/dev/null 2>&1; then
        local last_update=$(stat -c %Y "$HEARTBEAT_FILE")
    else
        local last_update=$(stat -f %m "$HEARTBEAT_FILE")
    fi

    local now=$(date +%s)
    local age_seconds=$((now - last_update))
    local age_minutes=$((age_seconds / 60))

    echo "$age_minutes"
    return 0
}

# =============================================================================
# SPAWN MINI CLAUDE
# =============================================================================

spawn_mini_claude() {
    local stuck_minutes="$1"

    log " Spawning mini Claude..."
    log "   Stuck duration: ${stuck_minutes} minutes"
    log "   Skill: $MINI_SKILL"

    # Build prompt for Claude
    local prompt="# Watchdog Mini - Quick Kick Mode

Ralph's heartbeat is stale (no update for ${stuck_minutes} minutes).

Please run the mini watchdog skill at: $MINI_SKILL

Follow the skill instructions exactly:
1. Check if Ralph is stuck
2. If stuck: Kick Ralph's ass with /ralph:discover
3. Log your findings
4. Exit

Provide a brief summary of what you found and did.
"

    # Run Claude with skill (5 minute timeout)
    cd "$PROJECT_DIR"
    local result
    result=$(timeout 300 claude -p "$prompt" 2>&1 || echo "TIMEOUT|Claude timed out")

    log " Claude result:"
    log "$result"

    # Log to file
    {
        echo "=== Mini Watchdog Claude Session - $(date) ==="
        echo "Stuck duration: ${stuck_minutes} minutes"
        echo "$result"
        echo "============================================="
    } >> "$LOG_FILE"

    log " Claude session complete"
}

# =============================================================================
# MAIN CHECK
# =============================================================================

main_check() {
    local run_number="$1"

    log "════════════════════════════════════════"
    log "Watchdog check #${run_number}/${MAX_RUNS}"
    log "════════════════════════════════════════"

    # Check heartbeat age
    local age_minutes
    age_minutes=$(check_heartbeat)

    if [[ -z "$age_minutes" ]]; then
        log " Could not check heartbeat (file may not exist)"
        age_minutes=999
    fi

    # Check if stuck
    if [ "$age_minutes" -ge "$STALE_MINUTES" ]; then
        log " Ralph is STUCK: ${age_minutes}min exceeds ${STALE_MINUTES}min threshold"
        spawn_mini_claude "$age_minutes"
    else
        log " Ralph is OK: heartbeat ${age_minutes}min old (fresh)"
    fi
}

# =============================================================================
# MAIN LOOP
# =============================================================================

main() {
    local mode="${1:-}"
    local interval_arg="${2:-}"
    local runs_arg="${3:-}"

    # Handle command-line arguments
    case "$mode" in
        --daemon|-d)
            run_as_daemon "$interval_arg" "$runs_arg"
            ;;
        --loop)
            # Just run the loop (called by daemon mode)
            INTERVAL_MINUTES="${interval_arg:-$DEFAULT_INTERVAL_MINUTES}"
            MAX_RUNS="${runs_arg:-$DEFAULT_MAX_RUNS}"
            # Set up trap for cleanup in loop mode
            trap cleanup_pid EXIT
            # Save PID for loop mode (the actual daemon process)
            save_pid
            ;;
        *)
            # Default: run in foreground
            # If first arg is a number, treat it as interval
            if [[ "$mode" =~ ^[0-9]+$ ]]; then
                INTERVAL_MINUTES="$mode"
                MAX_RUNS="${interval_arg:-$DEFAULT_MAX_RUNS}"
            else
                INTERVAL_MINUTES="$DEFAULT_INTERVAL_MINUTES"
                MAX_RUNS="$DEFAULT_MAX_RUNS"
            fi
            # Set up trap for cleanup in foreground mode
            trap cleanup_pid EXIT
            # Save PID for foreground mode
            save_pid
            ;;
    esac

    # Show banner only in foreground mode
    if [[ "$mode" != "--loop" ]]; then
        log "╔════════════════════════════════════════╗"
        log "║     Watchdog Mini - Quick Kick Mode      ║"
        log "╚════════════════════════════════════════╝"
        log "Interval: ${INTERVAL_MINUTES} minutes"
        log "Max runs: ${MAX_RUNS}"
        log "Skill: ~/.claude/skills/watchdog-mini.md"
        log "════════════════════════════════════════"
    fi

    local run_number=0

    while [ "$run_number" -lt "$MAX_RUNS" ]; do
        run_number=$((run_number + 1))
        main_check "$run_number"

        # Sleep until next check (unless last run)
        if [ "$run_number" -lt "$MAX_RUNS" ]; then
            local sleep_seconds=$((INTERVAL_MINUTES * 60))
            log " Sleeping ${INTERVAL_MINUTES}min until next check..."
            sleep "$sleep_seconds"
        fi
    done

    log "════════════════════════════════════════"
    log " Watchdog mini completed all ${MAX_RUNS} runs"
    log "════════════════════════════════════════"
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
