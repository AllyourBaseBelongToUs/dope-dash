#!/bin/bash
# ralph-tmux.sh - Ralph med TMUX context scraping
#
# "LLMs vet hur man driver TMUX. Tänk på loop backs -
# alla sätt som LLM:en automatiskt kan scrapa context."
# — Geoffrey Huntley
#
# Skapar TMUX-session med:
# - Pane 0: Dev server (npm run dev)
# - Pane 1: Ralph loop med context från pane 0
#
# Användning: ./ralph-tmux.sh <spec-fil> [dev-kommando]

set -e

SPEC_FILE="${1:-spec.md}"
DEV_CMD="${2:-npm run dev}"
SESSION="ralph-dev-$$"
MAX_ITERATIONS="${3:-30}"
COMPLETION_MARKER="<promise>DONE</promise>"

# Färger
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Ralph TMUX Mode ===${NC}"
echo "Session: $SESSION"
echo "Spec: $SPEC_FILE"
echo "Dev cmd: $DEV_CMD"
echo ""

# Verifiera spec finns
if [ ! -f "$SPEC_FILE" ]; then
    echo -e "${RED}Error: Spec-fil '$SPEC_FILE' hittades inte${NC}"
    exit 1
fi

# Skapa TMUX-session
tmux new-session -d -s "$SESSION" -x 200 -y 50

# Splitta horisontellt
tmux split-window -h -t "$SESSION"

# Pane 0 (vänster): Dev server
tmux send-keys -t "$SESSION:0.0" "$DEV_CMD 2>&1 | tee /tmp/ralph-dev-$$.log" Enter

# Vänta på att servern startar
sleep 3

# Pane 1 (höger): Ralph loop med context scraping
tmux send-keys -t "$SESSION:0.1" "
SPEC_FILE='$SPEC_FILE'
MAX_ITERATIONS=$MAX_ITERATIONS
COMPLETION_MARKER='$COMPLETION_MARKER'
BASE_PROMPT=\$(cat \"\$SPEC_FILE\")

echo '=== Ralph med TMUX Context ==='
echo ''

for i in \$(seq 1 \$MAX_ITERATIONS); do
    echo \"--- Iteration \$i/\$MAX_ITERATIONS ---\"

    # Scrapa context från dev server (senaste 30 rader)
    DEV_CONTEXT=\$(tail -30 /tmp/ralph-dev-$$.log 2>/dev/null || echo 'Ingen dev output')

    # Bygg prompt med context
    PROMPT=\"\$BASE_PROMPT

## Aktuell server-output (senaste 30 rader):
\\\`\\\`\\\`
\$DEV_CONTEXT
\\\`\\\`\\\`

Om det finns fel i server-outputen, fixa dem.\"

    # Kör Claude
    # VIKTIGT: Använd pipe istället för --print som hänger!
    OUTPUT=\$(echo \"\$PROMPT\" | claude --dangerously-skip-permissions 2>&1)
    echo \"\$OUTPUT\"

    # Kolla completion
    if echo \"\$OUTPUT\" | grep -q \"\$COMPLETION_MARKER\"; then
        echo ''
        echo '✅ Completion marker hittad!'
        echo \"Ralph klar efter \$i iterationer\"
        break
    fi

    sleep 2
done

echo ''
echo 'Tryck Enter för att avsluta TMUX-sessionen'
read
tmux kill-session -t $SESSION
" Enter

# Info
echo -e "${GREEN}TMUX-session startad!${NC}"
echo ""
echo "Kommandon:"
echo "  tmux attach -t $SESSION     # Visa sessionen"
echo "  tmux kill-session -t $SESSION  # Avsluta"
echo ""
echo -e "${YELLOW}Tip: Pane 0 = dev server, Pane 1 = Ralph${NC}"
echo ""

# Fråga om attach
read -p "Attacha till session? (y/n): " choice
if [ "$choice" = "y" ]; then
    tmux attach -t "$SESSION"
fi
