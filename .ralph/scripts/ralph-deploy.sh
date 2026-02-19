#!/bin/bash
#
# ralph-handoff.sh - Complete pipeline: Discovery → VM → Ralph
#
# Flow:
#   1. Run discovery locally (Claude Code)
#   2. Generate PRD + Skills
#   3. Push to VM
#   4. Start Ralph on VM
#   5. Monitor progress
#   6. Pull results when done
#
# Usage:
#   ./ralph-handoff.sh <project-name> [options]
#
# Options:
#   --input <file>     Start from meeting transcript
#   --skip-discovery   Skip discovery, use existing project
#   --watch            Watch VM progress after handoff
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Args
PROJECT_NAME="${1:-}"
INPUT_FILE=""
SKIP_DISCOVERY=false
WATCH_MODE=false
OVERNIGHT_MODE=false

# ntfy topic for notifications
NTFY_TOPIC="${NTFY_TOPIC:-}"

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: $0 <project-name> [options]"
    echo ""
    echo "Options:"
    echo "  --input <file>     Start from meeting transcript"
    echo "  --skip-discovery   Skip discovery, use existing project"
    echo "  --watch            Watch VM progress after handoff"
    echo "  --overnight        Nattläge: auto-stop VM, notify when done"
    echo ""
    echo "Examples:"
    echo "  $0 my-app                        # Full pipeline"
    echo "  $0 my-app --input meeting.md     # From transcript"
    echo "  $0 my-app --overnight            # Fire and forget"
    exit 1
fi

shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            shift
            INPUT_FILE="${1:-}"
            ;;
        --skip-discovery)
            SKIP_DISCOVERY=true
            ;;
        --watch)
            WATCH_MODE=true
            ;;
        --overnight)
            OVERNIGHT_MODE=true
            ;;
        *) ;;
    esac
    shift || true
done

# Helper: Send notification
notify() {
    local msg="$1"
    if [ -n "$NTFY_TOPIC" ]; then
        curl -s -d "$msg" "https://ntfy.sh/$NTFY_TOPIC" > /dev/null 2>&1 || true
    fi
}

PROJECT_DIR="./$PROJECT_NAME"

# ═══════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${MAGENTA}"
cat << 'EOF'
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║     ██████╗  █████╗ ██╗     ██████╗ ██╗  ██╗              ║
  ║     ██╔══██╗██╔══██╗██║     ██╔══██╗██║  ██║              ║
  ║     ██████╔╝███████║██║     ██████╔╝███████║              ║
  ║     ██╔══██╗██╔══██║██║     ██╔═══╝ ██╔══██║              ║
  ║     ██║  ██║██║  ██║███████╗██║     ██║  ██║              ║
  ║     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝              ║
  ║                                                           ║
  ║          H A N D O F F   P I P E L I N E                  ║
  ║                                                           ║
  ║     Discovery (local) → VM (cloud) → Ralph                ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "Projekt: ${GREEN}$PROJECT_NAME${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEG 1: DISCOVERY (lokal)
# ═══════════════════════════════════════════════════════════════
if [ "$SKIP_DISCOVERY" = false ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  STEG 1: DISCOVERY (lokal)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    DISCOVER_ARGS="$PROJECT_NAME"
    if [ -n "$INPUT_FILE" ]; then
        DISCOVER_ARGS="$DISCOVER_ARGS --input $INPUT_FILE"
    fi

    "$SCRIPT_DIR/ralph-discover.sh" $DISCOVER_ARGS

    echo ""
    echo -e "${GREEN}✓ Discovery klar${NC}"
fi

# Verify project exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Projekt saknas: $PROJECT_DIR${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════
# STEG 2: VALIDERA PROJEKT
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  STEG 2: VALIDERA PROJEKT${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check required files
REQUIRED_FILES=(
    "CLAUDE.md"
    "docs/prd.md"
)

MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PROJECT_DIR/$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (saknas)"
        MISSING=$((MISSING + 1))
    fi
done

# Count specs
SPEC_COUNT=$(ls -1 "$PROJECT_DIR/specs"/*.md 2>/dev/null | wc -l | tr -d ' ')
echo -e "  ${BLUE}○${NC} Specs: $SPEC_COUNT"

if [ $MISSING -gt 0 ]; then
    echo ""
    echo -e "${RED}Saknade filer. Kör discovery först.${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════
# STEG 3: PUSH TILL VM
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  STEG 3: PUSH TILL VM${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Start VM if not running
echo -e "${BLUE}Startar VM...${NC}"
"$SCRIPT_DIR/vm-sync.sh" start 2>/dev/null || true
sleep 5

# Push project
echo -e "${BLUE}Pushar projekt till VM...${NC}"
"$SCRIPT_DIR/vm-sync.sh" push "$PROJECT_DIR"

echo -e "${GREEN}✓ Projekt uppladdad till VM${NC}"

# ═══════════════════════════════════════════════════════════════
# STEG 4: STARTA RALPH PÅ VM
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  STEG 4: STARTA RALPH PÅ VM${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}Startar Ralph på VM...${NC}"
echo ""

# Run Ralph on VM in background (nohup)
"$SCRIPT_DIR/vm-sync.sh" run "specs/*.md" &
RALPH_PID=$!

echo -e "${GREEN}✓ Ralph startat (PID: $RALPH_PID)${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEG 5: MODE-SPECIFIC HANDLING
# ═══════════════════════════════════════════════════════════════
if [ "$OVERNIGHT_MODE" = true ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  OVERNIGHT MODE${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    notify "Ralph startat: $PROJECT_NAME (overnight mode)"

    # Create overnight wrapper script on VM
    OVERNIGHT_SCRIPT="#!/bin/bash
cd ~/workspace
echo 'Ralph overnight started: \$(date)' > ralph-overnight.log

# Run Ralph
./scripts/ralph.sh specs/*.md >> ralph-overnight.log 2>&1
EXIT_CODE=\$?

echo 'Ralph finished: \$(date)' >> ralph-overnight.log
echo 'Exit code: '\$EXIT_CODE >> ralph-overnight.log

# Notify
curl -s -d \"Ralph klar: $PROJECT_NAME (exit: \$EXIT_CODE)\" https://ntfy.sh/$NTFY_TOPIC || true

# Generate summary
SPECS_DONE=\$(grep -c 'DONE' ralph-overnight.log || echo 0)
SPECS_FAILED=\$(grep -c 'FAILED\\|Error' ralph-overnight.log || echo 0)
curl -s -d \"Specs: \$SPECS_DONE done, \$SPECS_FAILED issues\" https://ntfy.sh/$NTFY_TOPIC || true

# Stop VM to save money
echo 'Stopping VM...' >> ralph-overnight.log
sudo shutdown -h +5 'Ralph complete. VM stopping in 5 minutes.'
"

    # Push overnight script to VM
    echo "$OVERNIGHT_SCRIPT" | "$SCRIPT_DIR/vm-sync.sh" ssh "cat > ~/workspace/overnight.sh && chmod +x ~/workspace/overnight.sh"

    # Start overnight script in background with nohup
    "$SCRIPT_DIR/vm-sync.sh" ssh "cd ~/workspace && nohup ./overnight.sh > /dev/null 2>&1 &"

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  OVERNIGHT HANDOFF KLAR!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "Ralph kör nu autonomt på VM."
    echo ""
    echo -e "${YELLOW}Vad händer:${NC}"
    echo -e "  1. Ralph kör alla specs"
    echo -e "  2. Du får notification när klart (ntfy.sh/$NTFY_TOPIC)"
    echo -e "  3. VM stoppas automatiskt (sparar pengar)"
    echo ""
    echo -e "${YELLOW}Imorgon:${NC}"
    echo -e "  ${CYAN}./scripts/vm-sync.sh start${NC}        # Starta VM"
    echo -e "  ${CYAN}./scripts/vm-sync.sh pull $PROJECT_NAME${NC}  # Hämta resultat"
    echo -e "  ${CYAN}cat $PROJECT_NAME/ralph-overnight.log${NC}    # Se logg"
    echo ""
    echo -e "${BLUE}Sov gott!${NC}"
    echo ""

elif [ "$WATCH_MODE" = true ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  WATCH MODE${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Watching VM progress... (Ctrl+C för att avsluta)${NC}"
    echo ""

    # Wait for Ralph to finish
    wait $RALPH_PID || true

    echo ""
    echo -e "${GREEN}✓ Ralph klar!${NC}"
    echo ""

    # Pull results
    echo -e "${BLUE}Hämtar resultat...${NC}"
    "$SCRIPT_DIR/vm-sync.sh" pull "$PROJECT_DIR"

    # Stop VM to save money
    read -p "Stoppa VM för att spara pengar? [Y/n]: " STOP_VM
    STOP_VM=${STOP_VM:-y}
    if [[ "$STOP_VM" =~ ^[Yy] ]]; then
        "$SCRIPT_DIR/vm-sync.sh" stop
    fi
else
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  HANDOFF KLAR!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "Ralph kör nu på VM i bakgrunden."
    echo ""
    echo -e "${YELLOW}Kommandon:${NC}"
    echo -e "  ${CYAN}./scripts/vm-sync.sh ssh${NC}           # SSH till VM"
    echo -e "  ${CYAN}./scripts/vm-sync.sh pull $PROJECT_NAME${NC}  # Hämta resultat"
    echo -e "  ${CYAN}./scripts/vm-sync.sh stop${NC}          # Stoppa VM"
    echo ""
fi
