#!/bin/bash
# =============================================================================
# watchdog-full.sh - Full watchdog with granular lock file monitoring
#
# This script runs in cron on the VM (indefinite mode)
# When .working file is stale: Spawns Dog Claude -> collaborative troubleshooting
#
# Location: ~/watchdog-control/watchdog-full.sh (OUTSIDE project directory)
# Usage:
#   watchdog-full.sh [--daemon] [INTERVAL_MINUTES]
#   watchdog-full.sh --loop [INTERVAL_SECONDS]
#
# Examples:
#   watchdog-full.sh          # Run every 5 min (default), indefinite
#   watchdog-full.sh 10       # Run every 10 min, indefinite
#   watchdog-full.sh --daemon # Run as daemon in background
# =============================================================================

set -euo pipefail

# Configuration
WATCHDOG_DIR="$HOME/watchdog-control"
PROJECT_DIR="$HOME/projects/dope-dash"
HEARTBEAT_FILE="$PROJECT_DIR/.ralph/heartbeat.json"
WORKING_FILE="$PROJECT_DIR/.working"  # Granular lock file (updated frequently)
LOG_FILE="$PROJECT_DIR/.ralph/logs/watchdog-full.log"
DOG_SKILL="$HOME/.claude/skills/watchdog-dog.md"
STALE_MINUTES=20
PID_FILE="$WATCHDOG_DIR/watchdog.pid"

# Default interval (5 minutes = 300 seconds)
DEFAULT_INTERVAL_SECONDS=300

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
    local interval_seconds="${1:-$DEFAULT_INTERVAL_SECONDS}"

    check_already_running

    # Get the script directory
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Fork into background using nohup (reliable daemon approach)
    # We write the PID from within the child process using --loop mode
    nohup bash "$script_dir/watchdog-full.sh" --loop "$interval_seconds" </dev/null >/dev/null 2>&1 &

    # Wait a moment for the child to start and write its PID
    sleep 0.5

    # Check if PID file was created
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        echo "Watchdog started (PID: $pid)"
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
# CHECK GRANULAR LOCK FILE (Primary check - more reliable)
# =============================================================================

check_working_file() {
    if [[ ! -f "$WORKING_FILE" ]]; then
        # Don't log here - just return empty to indicate no file
        echo ""
        return 0
    fi

    local last_update
    last_update=$(cat "$WORKING_FILE" 2>/dev/null || echo "0")

    local now=$(date +%s)
    local age_seconds=$(echo "$now - $last_update" | bc)
    local age_minutes=$(echo "scale=0; $age_seconds / 60" | bc)

    echo "$age_minutes"
    return 0
}

# =============================================================================
# CHECK HEARTBEAT FILE (Secondary check - fallback)
# =============================================================================

check_heartbeat() {
    if [[ ! -f "$HEARTBEAT_FILE" ]]; then
        echo ""
        return 0
    fi

    local last_update
    if stat -c %Y "$HEARTBEAT_FILE" >/dev/null 2>&1; then
        last_update=$(stat -c %Y "$HEARTBEAT_FILE")
    else
        last_update=$(stat -f %m "$HEARTBEAT_FILE")
    fi

    local now=$(date +%s)
    local age_seconds=$((now - last_update))
    local age_minutes=$((age_seconds / 60))

    echo "$age_minutes"
    return 0
}

# =============================================================================
# CHECK PROCESS ACTIVITY (Tertiary check - is Claude actually running?)
# =============================================================================

check_process_activity() {
    # Check if Claude process exists (Ralph is actively working)
    if pgrep -f "claude" > /dev/null; then
        return 0  # Claude is running
    fi

    return 0  # No Claude process
}

# =============================================================================
# SPAWN DOG CLAUDE (COLLABORATIVE MODE)
# =============================================================================

spawn_dog_claude() {
    local stuck_minutes="$1"
    local reason="$2"

    log " Spawning Dog Claude (collaborative mode)..."
    log "   Stuck duration: ${stuck_minutes} minutes"
    log "   Reason: $reason"
    log "   Skill: $DOG_SKILL"

    # Build prompt for Claude
    local prompt="# Watchdog Full - Dog Claude Collaboration

Ralph's monitoring indicators are stale (no update for ${stuck_minutes} minutes).

Reason: $reason

Granular lock file age: ${stuck_minutes} minutes
Threshold: ${STALE_MINUTES} minutes

Please run the collaborative watchdog skill at: $DOG_SKILL

Follow the skill instructions exactly:
1. Check if Ralph is stuck (comprehensive diagnostics)
2. Determine if quick kick (mini skill) or full collaboration needed
3. Use helper protocol to communicate with Ralph if needed
4. Work WITH Ralph to resolve the issue
5. Log everything
6. Exit when done or escalate to human

Provide a comprehensive summary of your findings and actions.
"

    # Run Claude with skill (10 minute timeout for collaboration)
    cd "$PROJECT_DIR"
    local result
    result=$(timeout 600 claude -p "$prompt" 2>&1 || echo "TIMEOUT|Claude timed out")

    log " Claude result:"
    log "$result"

    # Log to file
    {
        echo "=== Full Watchdog Dog Claude Session - $(date) ==="
        echo "Stuck duration: ${stuck_minutes} minutes"
        echo "Reason: $reason"
        echo "$result"
        echo "================================================"
    } >> "$LOG_FILE"

    log " Claude session complete"
}

# =============================================================================
# MAIN CHECK
# =============================================================================

main_check() {
    log "──────────────────────────────────────────"
    log "Watchdog full check"
    log "──────────────────────────────────────────"

    # Primary check: Granular lock file (most reliable)
    local working_age
    working_age=$(check_working_file)

    # Secondary check: Heartbeat file
    local heartbeat_age
    heartbeat_age=$(check_heartbeat)

    # Tertiary check: Process activity
    local process_active
    if check_process_activity; then
        process_active="yes"
    else
        process_active="no"
    fi

    log " Metrics:"
    if [[ -z "$working_age" ]]; then
        log "   .working file: not found"
    else
        log "   .working file: ${working_age} minutes old"
    fi
    if [[ -z "$heartbeat_age" ]]; then
        log "   heartbeat.json: not found"
    else
        log "   heartbeat.json: ${heartbeat_age} minutes old"
    fi
    log "   Claude process: $process_active"

    # Decision tree: Is Ralph stuck?
    local should_intervene=false
    local reason=""

    # If .working file is stale AND heartbeat is stale -> Ralph is stuck
    if [[ -n "$working_age" ]] && [ "$working_age" -ge "$STALE_MINUTES" ]; then
        if [[ -n "$heartbeat_age" ]] && [ "$heartbeat_age" -ge "$STALE_MINUTES" ]; then
            should_intervene=true
            reason="Both .working and heartbeat are stale"
        elif [ "$process_active" = "no" ]; then
            should_intervene=true
            reason=".working stale and no Claude process running"
        fi
    fi

    # Also intervene if both files are stale (even if .working is slightly newer)
    if [[ -n "$heartbeat_age" ]] && [ "$heartbeat_age" -ge "$STALE_MINUTES" ]; then
        if [[ -n "$working_age" ]] && [ "$working_age" -ge $((STALE_MINUTES - 5)) ]; then
            should_intervene=true
            reason="Heartbeat is stale and .working is also stale"
        fi
    fi

    if [ "$should_intervene" = true ]; then
        log " Ralph is STUCK: ${reason}"
        spawn_dog_claude "${working_age:-${heartbeat_age}}" "$reason"
    else
        log " Ralph is OK: .working ${working_age:-N/A}min, heartbeat ${heartbeat_age:-N/A}min, Claude: $process_active"
    fi
}

# =============================================================================
# MAIN LOOP (INDEFINITE)
# =============================================================================

main() {
    local mode="${1:-}"
    local interval_arg="${2:-}"

    # Handle command-line arguments
    case "$mode" in
        --daemon|-d)
            run_as_daemon "$interval_arg"
            ;;
        --loop)
            # Just run the loop (called by daemon mode)
            CHECK_INTERVAL_SECONDS="${interval_arg:-$DEFAULT_INTERVAL_SECONDS}"
            # Set up trap for cleanup in loop mode
            trap cleanup_pid EXIT
            # Save PID for loop mode (the actual daemon process)
            save_pid
            ;;
        *)
            # Default: run in foreground
            # If first arg is a number, treat it as interval in minutes
            if [[ "$mode" =~ ^[0-9]+$ ]]; then
                CHECK_INTERVAL_SECONDS=$((${mode:-5} * 60))
            else
                CHECK_INTERVAL_SECONDS="$DEFAULT_INTERVAL_SECONDS"
            fi
            # Set up trap for cleanup in foreground mode
            trap cleanup_pid EXIT
            # Save PID for foreground mode
            save_pid
            ;;
    esac

    # Show banner only in foreground mode
    if [[ "$mode" != "--loop" ]]; then
        log "======================================================"
        log "     Watchdog Full - Granular Lock File Mode"
        log "======================================================"
        log "Check interval: $((CHECK_INTERVAL_SECONDS / 60)) minutes"
        log "Skill: ~/.claude/skills/watchdog-dog.md"
        log "Mode: Indefinite (run until stopped)"
        log "======================================================"
    fi

    # Run indefinitely
    while true; do
        main_check

        # Wait until next check
        log " Sleeping ${CHECK_INTERVAL_SECONDS}s until next check..."
        sleep "$CHECK_INTERVAL_SECONDS"
    done
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
