#!/bin/bash
# =============================================================================
# dog.sh - Watchdog control script (on VM)
#
# This script is executed on the VM via SSH from the /dog slash command
# It controls starting/stopping watchdogs in cron
#
# Location: ~/watchdog-control/dog.sh
#
# Usage:
#   dog                    # Show status
#   dog start mini         # Start mini watchdog
#   dog start full         # Start full watchdog
#   dog stop               # Stop any watchdog
#   dog restart [mini|full] # Restart watchdog
#   dog report [N]         # Show reports
# =============================================================================

set -euo pipefail

# Configuration
WATCHDOG_DIR="$HOME/watchdog-control"
PROJECT_DIR="$HOME/projects/dope-dash"
LOG_DIR="$PROJECT_DIR/.ralph/logs"
PID_FILE="$WATCHDOG_DIR/watchdog.pid"
LOCK_FILE="$WATCHDOG_DIR/watchdog.lock"

# Scripts
WATCHDOG_MINI="$WATCHDOG_DIR/watchdog-mini.sh"
WATCHDOG_FULL="$WATCHDOG_DIR/watchdog-full.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +%H:%M:%S)] ERROR: $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)] WARNING: $1${NC}" >&2
}

# =============================================================================
# SHOW STATUS
# =============================================================================

show_status() {
    echo -e "${BLUE}=== Watchdog Status ===${NC}"

    # Check if watchdog is running
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN} Watchdog running${NC}"
            echo "PID: $pid"
            ps -p "$pid" -o pid,etime,cmd || true

            # Show mode
            if [[ -f "$LOCK_FILE" ]]; then
                local mode=$(cat "$LOCK_FILE")
                echo "Mode: $mode"
            fi
        else
            echo -e "${YELLOW} PID file exists but process not running${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW} No watchdog running${NC}"
    fi

    # Show heartbeat status
    echo ""
    echo -e "${BLUE}=== Ralph Heartbeat ===${NC}"
    local heartbeat_file="$PROJECT_DIR/.ralph/heartbeat.json"
    if [[ -f "$heartbeat_file" ]]; then
        local last_update
        if stat -c %Y "$heartbeat_file" >/dev/null 2>&1; then
            last_update=$(stat -c %Y "$heartbeat_file")
        else
            last_update=$(stat -f %m "$heartbeat_file")
        fi
        local now=$(date +%s)
        local age_seconds=$((now - last_update))
        local age_minutes=$((age_seconds / 60))
        echo "Heartbeat age: ${age_minutes} minutes"
        if (( age_minutes < 20 )); then
            echo -e "${GREEN} Fresh${NC}"
        else
            echo -e "${RED} Stale (>20min)${NC}"
        fi
    else
        echo "No heartbeat file"
    fi
}

# =============================================================================
# STOP WATCHDOG
# =============================================================================

stop_watchdog() {
    echo -e "${BLUE}=== Stopping Watchdog ===${NC}"

    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")

        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping watchdog (PID: $pid)..."
            kill "$pid"
            sleep 1

            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                warn "Watchdog still running, forcing..."
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi

        rm -f "$PID_FILE"
        rm -f "$LOCK_FILE"
        log " Watchdog stopped"
    else
        # Try to find any watchdog processes
        local watchdog_pids
        watchdog_pids=$(pgrep -f "watchdog-(mini|full).sh" || true)
        if [[ -n "$watchdog_pids" ]]; then
            log "Stopping watchdog processes..."
            echo "$watchdog_pids" | xargs kill 2>/dev/null || true
            log " Watchdog stopped"
        else
            warn "No watchdog running"
        fi
    fi
}

# =============================================================================
# START MINI WATCHDOG
# =============================================================================

start_mini_watchdog() {
    local interval="${1:-15}"
    local runs="${2:-20}"

    log "Starting mini watchdog (every ${interval}min, ${runs} runs)..."

    if [[ ! -f "$WATCHDOG_MINI" ]]; then
        error "Mini watchdog script not found: $WATCHDOG_MINI"
        return 1
    fi

    # Stop any existing watchdog
    stop_watchdog

    # Use daemon mode instead of nohup
    "$WATCHDOG_MINI" --daemon "$interval" "$runs"

    log " Mini watchdog started"
}

# =============================================================================
# START FULL WATCHDOG
# =============================================================================

start_full_watchdog() {
    local interval="${1:-5}"

    log "Starting full watchdog (every ${interval}min, indefinite)..."

    if [[ ! -f "$WATCHDOG_FULL" ]]; then
        error "Full watchdog script not found: $WATCHDOG_FULL"
        return 1
    fi

    # Stop any existing watchdog
    stop_watchdog

    # Use daemon mode instead of nohup (interval is in minutes, convert to seconds for script)
    "$WATCHDOG_FULL" --daemon "$((interval * 60))"

    log " Full watchdog started"
}

# =============================================================================
# SHOW REPORTS
# =============================================================================

show_reports() {
    local count="${1:-10}"

    echo -e "${BLUE}=== Watchdog Reports ===${NC}"

    local reports_dir="$LOG_DIR"
    if [[ -d "$reports_dir" ]]; then
        # Show recent watchdog logs
        echo ""
        echo "Recent watchdog activity:"
        if [[ -f "$LOG_DIR/watchdog-mini.log" ]]; then
            echo "--- Mini watchdog ---"
            tail -n "$count" "$LOG_DIR/watchdog-mini.log" 2>/dev/null || true
        fi
        if [[ -f "$LOG_DIR/watchdog-full.log" ]]; then
            echo ""
            echo "--- Full watchdog ---"
            tail -n "$count" "$LOG_DIR/watchdog-full.log" 2>/dev/null || true
        fi
    else
        warn "No logs directory found: $reports_dir"
    fi
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    local command="${1:-status}"

    case "$command" in
        start)
            local mode="${2:-mini}"
            case "$mode" in
                mini)
                    start_mini_watchdog "${3:-15}" "${4:-20}"
                    ;;
                full)
                    start_full_watchdog "${3:-5}"
                    ;;
                *)
                    error "Unknown mode: $mode (use 'mini' or 'full')"
                    exit 1
                    ;;
            esac
            ;;

        stop)
            stop_watchdog
            ;;

        restart)
            local mode="${2:-}"
            if [[ -z "$mode" ]]; then
                # Read current mode from lock file
                if [[ -f "$LOCK_FILE" ]]; then
                    mode=$(cat "$LOCK_FILE")
                else
                    mode="mini"
                fi
            fi

            stop_watchdog
            sleep 1

            case "$mode" in
                mini)
                    start_mini_watchdog "${3:-15}" "${4:-20}"
                    ;;
                full)
                    start_full_watchdog "${3:-5}"
                    ;;
            esac
            ;;

        status|"")
            show_status
            ;;

        report|reports)
            show_reports "${2:-10}"
            ;;

        *)
            error "Unknown command: $command"
            echo ""
            echo "Usage:"
            echo "  dog                    # Show status"
            echo "  dog start mini         # Start mini watchdog"
            echo "  dog start full         # Start full watchdog"
            echo "  dog stop               # Stop watchdog"
            echo "  dog restart [mini|full] # Restart watchdog"
            echo "  dog report [N]         # Show reports"
            echo ""
            echo "Examples:"
            echo "  dog start mini 15 20   # Mini: every 15min, 20 times"
            echo "  dog start full 10      # Full: every 10min, indefinite"
            echo "  dog stop               # Stop any watchdog"
            echo "  dog report 5           # Show last 5 reports"
            exit 1
            ;;
    esac
}

main "$@"
