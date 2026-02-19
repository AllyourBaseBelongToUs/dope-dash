#!/bin/bash
# watch.sh - Fireplace dashboard
# Source this file: source lib/watch.sh

SPECS_DIR="${SPECS_DIR:-specs}"
CHECKSUM_DIR="${CHECKSUM_DIR:-.spec-checksums}"
LOG_DIR="${LOG_DIR:-ralph-logs}"
PROGRESS_FILE="${PROGRESS_FILE:-progress.txt}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Show live dashboard
show_watch() {
    echo -e "${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    🔥 RALPH DASHBOARD 🔥                      ║"
    echo "║                   Ctrl+C to exit                              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    while true; do
        clear
        echo -e "${MAGENTA}═══ RALPH DASHBOARD [$(date '+%H:%M:%S')] ═══${NC}"
        echo ""

        # Specs progress
        local total=$(ls -1 "$SPECS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
        local done=$(ls -1 "$CHECKSUM_DIR"/*.md5 2>/dev/null | wc -l | tr -d ' ')
        if [ "$total" -gt 0 ]; then
            local pct=$((done * 100 / total))
            echo -e "${YELLOW}Specs:${NC} ${GREEN}$done${NC}/$total ($pct%)"

            # Progress bar
            local w=40 f=$((pct * w / 100)) e=$((w - f))
            printf "  ["
            printf "%${f}s" | tr ' ' '█'
            printf "%${e}s" | tr ' ' '░'
            printf "]\n"
            echo ""
        fi

        # Worktrees
        local wt=$(git worktree list 2>/dev/null | wc -l | tr -d ' ')
        if [ "$wt" -gt 1 ]; then
            echo -e "${YELLOW}Worktrees:${NC} $wt"
            git worktree list 2>/dev/null | tail -n +2 | sed 's/^/  /'
            echo ""
        fi

        # Processes
        echo -e "${YELLOW}Processes:${NC}"
        local procs=$(ps aux | grep -E "ralph|claude" | grep -v grep | grep -v watch)
        if [ -n "$procs" ]; then
            echo "$procs" | awk '{printf "  %s %.1f%% CPU\n", $11, $3}' | head -5
        else
            echo "  (none)"
        fi
        echo ""

        # Recent commits
        if git rev-parse --git-dir > /dev/null 2>&1; then
            echo -e "${YELLOW}Recent commits:${NC}"
            git log --oneline -5 2>/dev/null | sed 's/^/  /'
            echo ""
        fi

        # Progress file
        if [ -f "$PROGRESS_FILE" ]; then
            echo -e "${YELLOW}Progress:${NC}"
            tail -3 "$PROGRESS_FILE" 2>/dev/null | sed 's/^/  /'
            echo ""
        fi

        echo -e "${BLUE}─────────────────────────────────────────${NC}"
        echo "  Updates every 5s. Ctrl+C to exit."

        sleep 5
    done
}
