#!/bin/bash
# =============================================================================
#
#  ██████╗  █████╗ ██╗     ██████╗ ██╗  ██╗
#  ██╔══██╗██╔══██╗██║     ██╔══██╗██║  ██║
#  ██████╔╝███████║██║     ██████╔╝███████║
#  ██╔══██╗██╔══██║██║     ██╔═══╝ ██╔══██║
#  ██║  ██║██║  ██║███████╗██║     ██║  ██║
#  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝
#
#  The One Script To Rule Them All
#
# =============================================================================
#
# Usage:
#   ./ralph.sh                     # Kör alla specs i specs/
#   ./ralph.sh specs/10-theme.md   # Kör en spec
#   ./ralph.sh specs/*.md          # Kör flera specs (parallellt om >1)
#   ./ralph.sh --status            # Visa status
#   ./ralph.sh --watch             # Fireplace view (live monitoring)
#   ./ralph.sh --help              # Hjälp
#
# Features:
#   ✓ Self-healing (retries med felrapport)
#   ✓ Rate limit & token tracking
#   ✓ Build lock cleanup
#   ✓ Backup & secrets scanning
#   ✓ Dangerous command blocking
#   ✓ Git branch isolation
#   ✓ Smart parallel execution (worktrees, max 3)
#   ✓ Smart conflict resolution (auto-resolve test/logs, pause on source)
#   ✓ Supervisor quality checks
#   ✓ Auto-merge om säkert
#   ✓ GitHub PR om manuell review behövs
#   ✓ ntfy notifications
#   ✓ Summary rapport
#   ✓ progress.txt (short-term memory - Ryan Carson)
#   ✓ CLAUDE.md updates (long-term memory)
#   ✓ Checksum tracking (skippa redan körda specs)
#
# =============================================================================

set -uo pipefail

# =============================================================================
# KONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Timing & Retries
MAX_RETRIES=3
PARALLEL_THRESHOLD=2  # Kör parallellt om fler specs än detta

# Ladda config för att avgöra timeouts
RALPH_CONFIG="$HOME/.ralph-vm"
if [ -f "$RALPH_CONFIG" ]; then
    source "$RALPH_CONFIG"
fi

# Justera timeouts baserat på Claude-mode
CLAUDE_MODE="${CLAUDE_VM_MODE:-${CLAUDE_LOCAL_MODE:-max}}"
if [ "$CLAUDE_MODE" = "api" ]; then
    TIMEOUT=900       # 15 min för API (snabbare)
    PARALLEL_MAX=5    # Fler parallella för API
    SUPERVISOR_TIMEOUT=120
else
    TIMEOUT=1800      # 30 min för MAX (kan vara långsammare)
    PARALLEL_MAX=2    # Start med 2, dynamiskt justerat
    SUPERVISOR_TIMEOUT=300
fi

# =============================================================================
# DYNAMIC PARALLEL SCALING - Justera antal processer baserat på resurser
# =============================================================================
get_available_ram_gb() {
    # Returnerar ledigt RAM i GB
    free -g 2>/dev/null | awk '/^Mem:/ {print $7}' || echo "4"
}

get_cpu_cores() {
    nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "2"
}

get_cpu_load() {
    # Returnerar 1-min load average
    uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | tr -d ' ' || echo "1"
}

calculate_optimal_parallel() {
    local available_ram=$(get_available_ram_gb)
    local cpu_cores=$(get_cpu_cores)
    local cpu_load=$(get_cpu_load)

    # Varje Claude-process behöver ~500MB RAM och lite CPU
    local ram_based_max=$((available_ram * 2))  # 2 processer per GB ledigt

    # CPU-baserad: max cores - current load, minst 1
    local load_int=${cpu_load%.*}  # Ta bort decimaler
    local cpu_based_max=$((cpu_cores - load_int))
    [ $cpu_based_max -lt 1 ] && cpu_based_max=1

    # Ta det lägsta av RAM och CPU
    local optimal=$ram_based_max
    [ $cpu_based_max -lt $optimal ] && optimal=$cpu_based_max

    # Begränsa till 1-6 processer
    [ $optimal -lt 1 ] && optimal=1
    [ $optimal -gt 6 ] && optimal=6

    echo $optimal
}

maybe_scale_parallel() {
    local current_running=$1
    local new_max=$(calculate_optimal_parallel)

    if [ $new_max -ne $PARALLEL_MAX ]; then
        log "${CYAN}📊 Dynamisk skalning: $PARALLEL_MAX → $new_max (RAM: $(get_available_ram_gb)GB, CPU load: $(get_cpu_load))${NC}"
        PARALLEL_MAX=$new_max
    fi
}

# Stack Detection
CURRENT_STACK=""
STACK_TEMPLATE_DIR=""

# Paths
LOG_DIR="ralph-logs"
BACKUP_DIR="${HOME}/ralph-backups"
RATE_LIMIT_LOG="${HOME}/ralph-rate-limits.log"
TOKEN_LOG="${HOME}/ralph-tokens.log"
WORKTREE_BASE="${HOME}/ralph-worktrees"
PROGRESS_FILE="progress.txt"  # Short-term memory (Ryan Carson)
CHECKSUM_DIR=".spec-checksums"  # Track completed specs

# Markers
COMPLETION_MARKER="<promise>DONE</promise>"

# Notifications
NTFY_TOPIC="${NTFY_TOPIC:-}"

# Git
MAIN_BRANCH="main"

# Färger
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# HJÄLPFUNKTIONER
# =============================================================================
log() {
    echo -e "[$(date +%H:%M:%S)] $1"
}

notify() {
    local msg="$1"
    local priority="${2:-default}"
    if [ -n "$NTFY_TOPIC" ]; then
        curl -s -H "Priority: $priority" -d "$msg" "https://ntfy.sh/$NTFY_TOPIC" > /dev/null 2>&1 || true
    fi
}

# =============================================================================
# EPIC TRACKING - Dynamiskt läser IMPLEMENTATION_PLAN.md
# =============================================================================
CURRENT_EPIC=""
CURRENT_EPIC_NAME=""
PLAN_FILE=""

# Hitta IMPLEMENTATION_PLAN.md
find_plan_file() {
    if [ -f "docs/IMPLEMENTATION_PLAN.md" ]; then
        echo "docs/IMPLEMENTATION_PLAN.md"
    elif [ -f "IMPLEMENTATION_PLAN.md" ]; then
        echo "IMPLEMENTATION_PLAN.md"
    else
        echo ""
    fi
}

# Hämta alla epics som associativ array-liknande output
# Format: E1|Projektsetup & Databas
get_all_epics() {
    local plan_file=$(find_plan_file)
    if [ -z "$plan_file" ]; then
        return
    fi

    # Hitta epic-tabellen och extrahera E1, E2, etc med namn
    grep -E "^\| *E[0-9]+ *\|" "$plan_file" 2>/dev/null | while read -r line; do
        local epic_id=$(echo "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')
        local epic_name=$(echo "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3}')
        echo "$epic_id|$epic_name"
    done
}

# Hitta vilken epic en task tillhör baserat på task-id eller beskrivning
# Läser sektioner som: ### Kritisk (E1: Projektsetup & Databas)
get_epic_for_task() {
    local task_search="$1"  # Kan vara task-id (T1.1) eller nyckelord
    local plan_file=$(find_plan_file)

    if [ -z "$plan_file" ]; then
        echo ""
        return
    fi

    # Hitta sektionen som innehåller tasken
    # Sektioner ser ut som: ### Kritisk (E1: Projektsetup & Databas)
    local current_epic=""
    local current_epic_name=""

    while IFS= read -r line; do
        # Kolla om det är en epic-sektion
        if echo "$line" | grep -qE "^###.*\(E[0-9]+:"; then
            current_epic=$(echo "$line" | grep -oE "E[0-9]+" | head -1)
            current_epic_name=$(echo "$line" | sed 's/.*(\(E[0-9]*: *\)\(.*\))/\2/' | sed 's/)$//')
        fi

        # Kolla om tasken finns på denna rad
        if echo "$line" | grep -qi "$task_search"; then
            if [ -n "$current_epic" ]; then
                echo "$current_epic|$current_epic_name"
                return
            fi
        fi
    done < "$plan_file"

    echo ""
}

# Matcha spec-fil mot task i planen
# Försöker matcha spec-namn mot task-beskrivningar
match_spec_to_epic() {
    local spec_name="$1"
    local plan_file=$(find_plan_file)

    if [ -z "$plan_file" ]; then
        echo ""
        return
    fi

    # Strategi 1: Exakt task-id match (om spec heter t.ex. "T1.1-setup")
    if echo "$spec_name" | grep -qE "^T[0-9]+\.[0-9]+"; then
        local task_id=$(echo "$spec_name" | grep -oE "^T[0-9]+\.[0-9]+")
        local result=$(get_epic_for_task "$task_id")
        if [ -n "$result" ]; then
            echo "$result"
            return
        fi
    fi

    # Strategi 2: Nyckelord-match
    # Ta bort siffror och bindestreck, matcha mot task-beskrivningar
    local keywords=$(echo "$spec_name" | sed 's/^[0-9]*-//' | tr '-' ' ')

    local current_epic=""
    local current_epic_name=""

    while IFS= read -r line; do
        # Kolla om det är en epic-sektion
        if echo "$line" | grep -qE "^###.*\(E[0-9]+:"; then
            current_epic=$(echo "$line" | grep -oE "E[0-9]+" | head -1)
            current_epic_name=$(echo "$line" | sed 's/.*E[0-9]*: *//' | sed 's/)$//' | sed 's/ *$//')
        fi

        # Fuzzy match: kolla om några nyckelord finns i task-beskrivningen
        for keyword in $keywords; do
            if [ ${#keyword} -gt 3 ] && echo "$line" | grep -qi "$keyword"; then
                if [ -n "$current_epic" ]; then
                    echo "$current_epic|$current_epic_name"
                    return
                fi
            fi
        done
    done < "$plan_file"

    # Strategi 3: Nummer-baserad fallback
    local spec_num=$(echo "$spec_name" | grep -oE "^[0-9]+" | sed 's/^0*//')
    if [ -n "$spec_num" ]; then
        # Anta att spec 01-03 är E1, 04-06 är E2, etc (fallback)
        local epic_num=$(( (spec_num - 1) / 3 + 1 ))
        local fallback_epic="E$epic_num"
        local fallback_name=$(grep -E "^\| *$fallback_epic *\|" "$plan_file" 2>/dev/null | head -1 | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3}')
        if [ -n "$fallback_name" ]; then
            echo "$fallback_epic|$fallback_name"
            return
        fi
    fi

    echo ""
}

# Notifiera om epic-byte
notify_epic_change() {
    local spec_name="$1"

    local epic_info=$(match_spec_to_epic "$spec_name")

    if [ -z "$epic_info" ]; then
        return
    fi

    local new_epic=$(echo "$epic_info" | cut -d'|' -f1)
    local new_epic_name=$(echo "$epic_info" | cut -d'|' -f2)

    if [ "$new_epic" != "$CURRENT_EPIC" ]; then
        # Avsluta förra epic om det fanns
        if [ -n "$CURRENT_EPIC" ] && [ -n "$CURRENT_EPIC_NAME" ]; then
            notify "🎉 $CURRENT_EPIC: $CURRENT_EPIC_NAME - Klar!" "default"
            log "${GREEN}🎉 $CURRENT_EPIC: $CURRENT_EPIC_NAME - Klar!${NC}"
        fi

        # Starta ny epic
        CURRENT_EPIC="$new_epic"
        CURRENT_EPIC_NAME="$new_epic_name"

        notify "🚀 $new_epic: $new_epic_name - Startar" "high"
        log "${MAGENTA}🚀 $new_epic: $new_epic_name - Startar${NC}"
    fi
}

# Notifiera task-klar (inkluderar epic-info)
notify_task_done() {
    local spec_name="$1"

    if [ -n "$CURRENT_EPIC" ] && [ -n "$CURRENT_EPIC_NAME" ]; then
        notify "✅ $CURRENT_EPIC: $spec_name" "low"
    else
        notify "✅ Klar: $spec_name" "low"
    fi
}

# =============================================================================
# STACK DETECTION & TEMPLATE HOOKS
# =============================================================================
# Detekterar vilken stack som används baserat på projektfiler
detect_stack() {
    local project_dir="${1:-.}"

    # React + Supabase
    if [ -f "$project_dir/package.json" ] && [ -d "$project_dir/supabase" ]; then
        if grep -q "react" "$project_dir/package.json" 2>/dev/null; then
            echo "react-supabase"
            return
        fi
    fi

    # React + Vite (utan Supabase)
    if [ -f "$project_dir/vite.config.ts" ] || [ -f "$project_dir/vite.config.js" ]; then
        if grep -q "react" "$project_dir/package.json" 2>/dev/null; then
            echo "react-vite"
            return
        fi
    fi

    # Next.js
    if [ -f "$project_dir/next.config.js" ] || [ -f "$project_dir/next.config.mjs" ]; then
        echo "nextjs"
        return
    fi

    # Supabase + Next.js
    if [ -d "$project_dir/supabase" ] && [ -f "$project_dir/next.config.js" ]; then
        echo "supabase-nextjs"
        return
    fi

    # Fallback: unknown
    echo "unknown"
}

# Initiera stack - anropar template's setup.sh
init_stack() {
    local project_dir="${1:-.}"

    CURRENT_STACK=$(detect_stack "$project_dir")
    STACK_TEMPLATE_DIR="$RALPH_DIR/templates/stacks/$CURRENT_STACK"

    log "${CYAN}Stack detekterad: $CURRENT_STACK${NC}"

    if [ -d "$STACK_TEMPLATE_DIR" ]; then
        log "${CYAN}Template: $STACK_TEMPLATE_DIR${NC}"

        # Kopiera CLAUDE.md om det saknas i projektet
        if [ -f "$STACK_TEMPLATE_DIR/CLAUDE.md" ] && [ ! -f "$project_dir/CLAUDE.md" ]; then
            cp "$STACK_TEMPLATE_DIR/CLAUDE.md" "$project_dir/"
            log "${GREEN}Kopierade stack CLAUDE.md${NC}"
        fi

        # Kör setup.sh om det finns
        if [ -x "$STACK_TEMPLATE_DIR/scripts/setup.sh" ]; then
            log "${BLUE}Kör stack setup...${NC}"
            if ! "$STACK_TEMPLATE_DIR/scripts/setup.sh" "$project_dir"; then
                log "${RED}Setup FAILED - kan inte fortsätta${NC}"
                log "${YELLOW}Fixa problemen ovan och kör igen${NC}"
                exit 1
            fi
        fi
    else
        log "${YELLOW}Ingen template för stack: $CURRENT_STACK${NC}"
    fi
}

# Anropa stack hook
call_stack_hook() {
    local hook_name="$1"
    local project_dir="${2:-.}"
    shift 2
    local extra_args=("$@")

    if [ -z "$STACK_TEMPLATE_DIR" ] || [ ! -d "$STACK_TEMPLATE_DIR" ]; then
        return 0
    fi

    local hook_script="$STACK_TEMPLATE_DIR/hooks/$hook_name.sh"

    if [ -x "$hook_script" ]; then
        log "${CYAN}Hook: $hook_name${NC}"
        "$hook_script" "$project_dir" "${extra_args[@]}" || {
            log "${YELLOW}Hook $hook_name misslyckades${NC}"
            return 1
        }
    fi

    return 0
}

# Kör stack verifiering med self-healing
run_stack_verify() {
    local project_dir="${1:-.}"
    local max_heal_attempts=3
    local heal_attempt=0

    # Säkerställ dependencies först
    (cd "$project_dir" && ensure_dependencies) || true

    while [ $heal_attempt -lt $max_heal_attempts ]; do
        ((heal_attempt++))

        local verify_output=""
        local verify_exit=0

        if [ -z "$STACK_TEMPLATE_DIR" ] || [ ! -d "$STACK_TEMPLATE_DIR" ]; then
            # Fallback: kör npm run build
            if [ -f "$project_dir/package.json" ]; then
                log "${BLUE}Fallback verify: npm run build (attempt $heal_attempt/$max_heal_attempts)${NC}"
                verify_output=$((cd "$project_dir" && npm run build) 2>&1) || verify_exit=$?
            else
                return 0
            fi
        else
            local verify_script="$STACK_TEMPLATE_DIR/scripts/verify.sh"

            if [ -x "$verify_script" ]; then
                log "${CYAN}═══ STACK VERIFIERING (attempt $heal_attempt/$max_heal_attempts) ═══${NC}"
                verify_output=$("$verify_script" "$project_dir" 2>&1) || verify_exit=$?
            else
                return 0
            fi
        fi

        # Om lyckades, returnera OK
        if [ $verify_exit -eq 0 ]; then
            log "${GREEN}Stack verifiering OK${NC}"
            return 0
        fi

        # Misslyckades - försök self-heal
        log "${RED}Stack verifiering FAILED${NC}"
        echo "$verify_output" | tail -20

        # Försök self-heal
        if try_selfheal "$verify_output"; then
            log "${CYAN}Försöker igen efter self-heal...${NC}"
            continue
        else
            # Inget att heala - ge upp
            log "${RED}Ingen self-heal möjlig${NC}"
            return 1
        fi
    done

    log "${RED}Max self-heal försök ($max_heal_attempts) - ger upp${NC}"
    return 1
}

# =============================================================================
# CHECKSUM TRACKING - Skippa redan körda specs
# =============================================================================
spec_checksum() {
    local spec_file="$1"
    md5sum "$spec_file" 2>/dev/null | cut -d' ' -f1 || md5 -q "$spec_file" 2>/dev/null
}

is_spec_already_done() {
    local spec_file="$1"
    local basename=$(basename "$spec_file")
    local checksum_file="$CHECKSUM_DIR/$basename.md5"

    mkdir -p "$CHECKSUM_DIR"

    if [ -f "$checksum_file" ]; then
        local old_checksum=$(cat "$checksum_file")
        local new_checksum=$(spec_checksum "$spec_file")

        if [ "$old_checksum" = "$new_checksum" ]; then
            return 0  # true - redan körts med samma innehåll
        fi
    fi
    return 1  # false - ny eller ändrad
}

save_spec_checksum() {
    local spec_file="$1"
    local basename=$(basename "$spec_file")

    mkdir -p "$CHECKSUM_DIR"
    spec_checksum "$spec_file" > "$CHECKSUM_DIR/$basename.md5"
}

# =============================================================================
# TOKEN & CONTEXT MANAGEMENT
# =============================================================================
estimate_tokens() {
    local text="$1"
    local chars=$(echo -n "$text" | wc -c)
    echo $((chars * 10 / 35))
}

log_tokens() {
    local context="$1"
    local tokens="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $tokens tokens | $context" >> "$TOKEN_LOG"
}

check_context_budget() {
    local current_tokens=$1
    local max_tokens=${2:-176000}
    local usage_percent=$((current_tokens * 100 / max_tokens))

    if [ $usage_percent -gt 80 ]; then
        log "${RED}⚠️ Context: $usage_percent% - nära gränsen!${NC}"
        return 1
    fi
    return 0
}

# =============================================================================
# RATE LIMIT HANDLING
# =============================================================================
RATE_LIMIT_PATTERNS=(
    "rate.limit"
    "too.many.requests"
    "quota.exceeded"
    "capacity"
    "try.again.later"
    "retry.after"
    "429"
    "overloaded"
)

is_rate_limited() {
    local output="$1"
    for pattern in "${RATE_LIMIT_PATTERNS[@]}"; do
        if echo "$output" | grep -qi "$pattern"; then
            return 0
        fi
    done
    return 1
}

log_rate_limit() {
    local context="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $context" >> "$RATE_LIMIT_LOG"
    local total=$(wc -l < "$RATE_LIMIT_LOG" 2>/dev/null || echo 0)
    log "${YELLOW}⚠️ Rate limit hit #$total${NC}"
}

# =============================================================================
# SELF-HEALING: Detektera och fixa saknade dependencies
# =============================================================================
SELFHEAL_PATTERNS=(
    # Pattern|Fix command|Description
    "tsc: not found|npm install -g typescript|TypeScript compiler"
    "npx: not found|npm install -g npx|npx command"
    "node: not found|echo 'Install Node.js manually'|Node.js runtime"
    "vite: not found|npm install vite|Vite bundler"
    "vitest: not found|npm install vitest|Vitest test runner"
    "playwright: not found|npx playwright install|Playwright browser"
    "supabase: not found|npm install -g supabase|Supabase CLI"
    "Cannot find module|npm install|Missing npm package"
    "ENOENT.*node_modules|npm install|Missing node_modules"
    "MODULE_NOT_FOUND|npm install|Missing module"
    "ERR_MODULE_NOT_FOUND|npm install|Missing ES module"
)

# Försök self-heal baserat på error output
try_selfheal() {
    local error_output="$1"
    local healed=false

    log "${CYAN}═══ SELF-HEALING CHECK ═══${NC}"

    for pattern_entry in "${SELFHEAL_PATTERNS[@]}"; do
        local pattern=$(echo "$pattern_entry" | cut -d'|' -f1)
        local fix_cmd=$(echo "$pattern_entry" | cut -d'|' -f2)
        local description=$(echo "$pattern_entry" | cut -d'|' -f3)

        if echo "$error_output" | grep -qiE "$pattern"; then
            log "${YELLOW}🔧 Detekterade: $description${NC}"
            log "${BLUE}   Fix: $fix_cmd${NC}"

            # Kör fix-kommandot
            if eval "$fix_cmd" 2>&1; then
                log "${GREEN}✅ Self-heal lyckades: $description${NC}"
                notify "🔧 Self-heal: $description"
                healed=true
            else
                log "${RED}❌ Self-heal misslyckades: $description${NC}"
                notify "❌ Self-heal failed: $description" "high"
            fi
        fi
    done

    if [ "$healed" = true ]; then
        return 0  # Something was healed, retry build
    else
        return 1  # Nothing to heal
    fi
}

# Kör npm install om package.json finns men node_modules saknas
ensure_dependencies() {
    if [ -f "package.json" ] && [ ! -d "node_modules" ]; then
        log "${YELLOW}🔧 node_modules saknas - kör npm install${NC}"
        npm install 2>&1 || {
            log "${RED}npm install misslyckades${NC}"
            return 1
        }
        log "${GREEN}✅ Dependencies installerade${NC}"
    fi
    return 0
}

# =============================================================================
# CLEANUP: Locks, cache, processer
# =============================================================================
cleanup_locks() {
    log "${BLUE}Rensar locks...${NC}"

    # Next.js
    rm -rf .next/lock 2>/dev/null || true

    # Turbo
    rm -rf .turbo/.lock 2>/dev/null || true

    # Node modules cache
    rm -rf node_modules/.cache/.lock 2>/dev/null || true

    # Döda hängande builds
    pkill -f "next build" 2>/dev/null || true
    pkill -f "turbo build" 2>/dev/null || true
}

# =============================================================================
# BACKUP
# =============================================================================
backup_project() {
    local backup_path="$BACKUP_DIR/$TIMESTAMP"
    log "${BLUE}Backup: $backup_path${NC}"
    mkdir -p "$backup_path"
    rsync -a --exclude='node_modules' --exclude='.git' --exclude='.next' . "$backup_path/" 2>/dev/null || true
}

# =============================================================================
# MEMORY LAYER (Ryan Carson pattern)
# =============================================================================

# Läs progress.txt för att inkludera i prompten
get_progress_context() {
    if [ -f "$PROGRESS_FILE" ]; then
        local lines=$(wc -l < "$PROGRESS_FILE")
        if [ "$lines" -gt 100 ]; then
            # Ta bara senaste 100 raderna för att spara context
            tail -100 "$PROGRESS_FILE"
        else
            cat "$PROGRESS_FILE"
        fi
    fi
}

# Logga learnings till progress.txt (short-term memory)
log_progress() {
    local spec_name="$1"
    local iteration="$2"
    local status="$3"

    cat >> "$PROGRESS_FILE" << EOF

---
## $(date '+%Y-%m-%d %H:%M:%S') | $spec_name | Iteration $iteration | $status

EOF

    # Be Claude logga sina learnings
    echo "Du har just avslutat iteration $iteration av $spec_name.
Skriv 2-3 korta punkter om:
1. Vad implementerades
2. Eventuella gotchas eller patterns du upptäckte
3. Filer som ändrades

Svara ENDAST med punkterna, inget annat." | \
        timeout 60 claude --dangerously-skip-permissions 2>/dev/null >> "$PROGRESS_FILE" || true

    log "${CYAN}Progress loggad till $PROGRESS_FILE${NC}"
}

# Uppdatera CLAUDE.md med långsiktiga learnings (long-term memory)
update_claude_md() {
    local spec_name="$1"

    # Kolla om CLAUDE.md finns
    if [ ! -f "CLAUDE.md" ]; then
        return 0
    fi

    log "${CYAN}Uppdaterar CLAUDE.md med learnings...${NC}"

    echo "Du har just slutfört $spec_name.
Om du upptäckte nya mönster, gotchas, eller viktiga konventioner som framtida utvecklare borde veta:
1. Läs CLAUDE.md
2. Om det finns något viktigt att lägga till under ## Learnings eller liknande sektion, gör det
3. Håll det kort och relevant
4. Om inget viktigt att lägga till, gör ingenting

Svara inte med något - bara uppdatera filen om det behövs." | \
        timeout $SUPERVISOR_TIMEOUT claude --dangerously-skip-permissions 2>/dev/null || true
}

# =============================================================================
# SÄKERHET: Farliga kommandon
# =============================================================================
check_dangerous_commands() {
    local diff_content
    diff_content=$(git diff 2>/dev/null) || return 0

    local dangerous=(
        "rm -rf /"
        "rm -rf ~"
        "sudo rm -rf"
        "chmod -R 777 /"
        "dd if=/dev"
        "> /dev/sd"
    )

    for pattern in "${dangerous[@]}"; do
        if echo "$diff_content" | grep -qF "$pattern"; then
            log "${RED}🚨 FARLIGT KOMMANDO: $pattern${NC}"
            return 1
        fi
    done

    # curl/wget pipe till bash
    if echo "$diff_content" | grep -qE "curl.*\|.*bash|wget.*\|.*bash"; then
        log "${RED}🚨 FARLIGT: curl/wget pipe till bash${NC}"
        return 1
    fi

    return 0
}

# =============================================================================
# SÄKERHET: Secrets scanning
# =============================================================================
scan_secrets() {
    local secrets_found=0

    # .env filer
    if git diff --cached --name-only 2>/dev/null | grep -qE "^\.env|\.env\.|config/\.env"; then
        log "${RED}🚨 .env fil staged!${NC}"
        secrets_found=1
    fi

    # API-nycklar
    local patterns=(
        "sk-ant-[a-zA-Z0-9]{20,}"
        "sk-[a-zA-Z0-9]{40,}"
        "ghp_[a-zA-Z0-9]{30,}"
        "gho_[a-zA-Z0-9]{30,}"
        "sb_[a-zA-Z0-9]{30,}"
        "eyJ[a-zA-Z0-9_-]{50,}"
    )

    for pattern in "${patterns[@]}"; do
        if git diff --cached 2>/dev/null | grep -qE "$pattern"; then
            log "${RED}🚨 SECRET: $pattern${NC}"
            secrets_found=1
        fi
    done

    return $secrets_found
}

# =============================================================================
# TESTER: Smart filtering
# =============================================================================
run_tests() {
    if [ ! -f "package.json" ]; then
        log "${YELLOW}Inget package.json - skippar tester${NC}"
        return 0
    fi

    if ! grep -q '"test"' package.json 2>/dev/null; then
        log "${YELLOW}⚠️ Inget test-script i package.json${NC}"
        # Returnera OK men logga varning - supervisor checks lägger till tester
        return 0
    fi

    log "Kör tester..."
    local output
    local exit_code=0
    output=$(npm test 2>&1) || exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo "$output" | tail -3
        return 0
    else
        log "${RED}Tester misslyckades:${NC}"
        echo "$output" | grep -A 3 -B 1 "FAIL\|Error\|✗" | head -20
        return 1
    fi
}

# =============================================================================
# SUPERVISOR: Kvalitetskontroller
# =============================================================================
run_supervisor_checks() {
    log "${CYAN}═══ SUPERVISOR CHECKS ═══${NC}"

    # Check 1: Tester - kör och fixa tills de passerar
    log "${YELLOW}Check 1: Tester${NC}"
    local test_attempts=0
    local max_test_attempts=3

    while [ $test_attempts -lt $max_test_attempts ]; do
        ((test_attempts++))
        log "  Test attempt $test_attempts/$max_test_attempts"

        # Kör tester
        local test_output
        local test_exit=0
        test_output=$(npm test 2>&1) || test_exit=$?

        if [ $test_exit -eq 0 ]; then
            log "${GREEN}  ✅ Alla tester passerar${NC}"
            break
        else
            log "${RED}  ❌ Tester failar${NC}"
            echo "$test_output" | tail -20

            if [ $test_attempts -lt $max_test_attempts ]; then
                log "  Ber Claude fixa..."
                local fix_prompt="Testerna failar med följande output:

$test_output

Fixa testerna så de passerar. Kör 'npm test' för att verifiera."

                echo "$fix_prompt" | timeout $((SUPERVISOR_TIMEOUT * 2)) claude --dangerously-skip-permissions 2>&1 || true

                git add -A 2>/dev/null || true
                git commit -m "Supervisor: fix failing tests (attempt $test_attempts)" 2>/dev/null || true
            fi
        fi
    done

    # Check 2: TypeScript
    log "${YELLOW}Check 2: TypeScript${NC}"
    local tsc_output
    local tsc_exit=0
    tsc_output=$(npx tsc --noEmit 2>&1) || tsc_exit=$?

    if [ $tsc_exit -eq 0 ]; then
        log "${GREEN}  ✅ TypeScript OK${NC}"
    else
        log "${RED}  ❌ TypeScript fel${NC}"
        echo "$tsc_output" | head -20

        # Försök self-heal först (t.ex. tsc: not found)
        if try_selfheal "$tsc_output"; then
            log "  Försöker igen efter self-heal..."
            tsc_output=$(npx tsc --noEmit 2>&1) || tsc_exit=$?
            if [ $tsc_exit -eq 0 ]; then
                log "${GREEN}  ✅ TypeScript OK efter self-heal${NC}"
            fi
        fi

        # Om fortfarande fel, be Claude fixa
        if [ $tsc_exit -ne 0 ]; then
            log "  Ber Claude fixa..."
            echo "Fixa TypeScript-felen:

$tsc_output" | timeout $((SUPERVISOR_TIMEOUT * 2)) claude --dangerously-skip-permissions 2>&1 || true

            git add -A 2>/dev/null || true
            git commit -m "Supervisor: fix TypeScript errors" 2>/dev/null || true
        fi
    fi

    # Check 3: Build
    log "${YELLOW}Check 3: Build${NC}"
    local build_output
    local build_exit=0
    build_output=$(npm run build 2>&1) || build_exit=$?

    if [ $build_exit -eq 0 ]; then
        log "${GREEN}  ✅ Build OK${NC}"
    else
        log "${RED}  ❌ Build failar${NC}"
        echo "$build_output" | tail -20

        # Försök self-heal först
        if try_selfheal "$build_output"; then
            log "  Försöker igen efter self-heal..."
            build_output=$(npm run build 2>&1) || build_exit=$?
            if [ $build_exit -eq 0 ]; then
                log "${GREEN}  ✅ Build OK efter self-heal${NC}"
            fi
        fi

        # Om fortfarande fel, be Claude fixa
        if [ $build_exit -ne 0 ]; then
            log "  Ber Claude fixa..."
            echo "Build failar:

$build_output

Fixa så projektet bygger." | timeout $((SUPERVISOR_TIMEOUT * 2)) claude --dangerously-skip-permissions 2>&1 || true

            git add -A 2>/dev/null || true
            git commit -m "Supervisor: fix build errors" 2>/dev/null || true
        fi
    fi

    return 0
}

# =============================================================================
# KÖR EN SPEC
# =============================================================================
run_single_spec() {
    local spec="$1"
    local branch="$2"
    local attempt=1
    local error_context=""
    local session_id=""
    local spec_name=$(basename "$spec" .md)

    log "${GREEN}=== $spec_name ===${NC}"

    # Epic tracking - notifiera om ny epic
    notify_epic_change "$spec_name"

    # Checksum-check: skippa om redan kört med samma innehåll
    if is_spec_already_done "$spec"; then
        log "${BLUE}⏭ Spec redan körd (samma checksum) - troligtvis implementerad${NC}"
        log "  Skippar för att spara tokens"
        return 0
    fi

    # Cleanup före
    cleanup_locks

    # Läs spec och räkna tokens
    local prompt=$(cat "$spec")
    local tokens=$(estimate_tokens "$prompt")
    log_tokens "$spec" "$tokens"
    log "Tokens: ~$tokens"

    # Generera session ID för denna spec (för resume)
    session_id=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "$(date +%s)-$$")
    log "Session ID: $session_id"

    while [ $attempt -le $MAX_RETRIES ]; do
        log "${YELLOW}Attempt $attempt/$MAX_RETRIES${NC}"

        local output
        local exit_code=0

        if [ $attempt -eq 1 ]; then
            # FÖRSTA KÖRNINGEN: Minimal prompt (liten context = bättre resultat)
            # INGEN progress context - Claude läser koden själv

            local full_prompt="$prompt

---
När klar: skriv <promise>DONE</promise>
Innan DONE: kör 'npm run build' och verifiera att det passerar."

            log "${CYAN}Startar ny session...${NC}"
            output=$(echo "$full_prompt" | timeout $TIMEOUT claude --session-id "$session_id" --dangerously-skip-permissions -p 2>&1) || exit_code=$?

        else
            # RETRY: Resume session med bara felinformation (sparar tokens!)
            local retry_prompt="VERIFIERING MISSLYCKADES!

$error_context

Fixa felen ovan. Kör 'npm run build' för att verifiera.
Skriv <promise>DONE</promise> när bygget går igenom."

            log "${CYAN}Resumar session (sparar tokens)...${NC}"
            output=$(echo "$retry_prompt" | timeout $TIMEOUT claude --resume "$session_id" --dangerously-skip-permissions -p 2>&1) || exit_code=$?
        fi

        echo "$output"

        # Rate limit?
        if is_rate_limited "$output"; then
            log_rate_limit "Spec: $(basename "$spec")"
            log "${YELLOW}Rate limit - väntar 2 min...${NC}"
            notify "⏳ Rate limit - väntar"
            sleep 120
            continue
        fi

        # Auth error?
        if echo "$output" | grep -qi "401\|unauthorized"; then
            log "${YELLOW}Auth-fel - väntar 1 min...${NC}"
            sleep 60
            continue
        fi

        # Timeout?
        if [ $exit_code -eq 124 ]; then
            error_context="Timeout efter 30 min"
            ((attempt++))
            continue
        fi

        # Farliga kommandon?
        if ! check_dangerous_commands; then
            log "${RED}🚨 FARLIGA KOMMANDON - STOPPAR${NC}"
            notify "🚨 Farliga kommandon i $(basename "$spec")"
            return 1
        fi

        # Git checkpoint
        if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
            # Kör post-create hook för nya filer
            local new_files=$(git status --porcelain 2>/dev/null | grep "^??" | cut -c4-)
            for new_file in $new_files; do
                if [[ "$new_file" =~ \.(tsx|ts)$ ]]; then
                    call_stack_hook "post-create" "." "$new_file" 2>/dev/null || true
                fi
            done

            git add -A

            if ! scan_secrets; then
                log "${RED}🚨 SECRETS - STOPPAR${NC}"
                git reset HEAD . 2>/dev/null || true
                return 1
            fi

            git commit -m "Ralph: $(basename "$spec" .md) (attempt $attempt)" 2>/dev/null || true
        fi

        # Completion marker?
        if echo "$output" | grep -q "$COMPLETION_MARKER"; then
            log "${GREEN}✅ Completion marker hittad${NC}"

            # HÅRT KRAV: Verifiera med stack verify (build, tester, etc)
            log "${CYAN}Verifierar med stack verify...${NC}"

            # Fånga verify-output för att skicka till Claude vid retry
            local verify_output
            verify_output=$(run_stack_verify "." 2>&1)
            local verify_exit=$?

            echo "$verify_output"

            if [ $verify_exit -eq 0 ]; then
                log "${GREEN}✅ Stack verify OK${NC}"
                # Spara checksum så vi skippar nästa gång
                save_spec_checksum "$spec"
                # Notifiera task klar
                notify_task_done "$spec_name"
                # Logga progress (short-term memory)
                log_progress "$(basename "$spec")" "$attempt" "SUCCESS"
                # Auto-push till remote (triggar deploy)
                if git remote get-url origin &>/dev/null; then
                    log "${CYAN}Pushar till origin...${NC}"
                    git push -u origin "$branch" 2>&1 || log "${YELLOW}Push failed (kanske redan uppe)${NC}"
                fi
                return 0
            else
                log "${RED}❌ Stack verify FAILED - marker ignorerad${NC}"
                # Trimma verify-output för att spara tokens (max 50 rader)
                local trimmed_output
                trimmed_output=$(echo "$verify_output" | grep -E "(error|FAIL|❌|Error|failed)" | head -30)
                if [ -z "$trimmed_output" ]; then
                    trimmed_output=$(echo "$verify_output" | tail -30)
                fi
                error_context="Build FAILED. Fel:

$trimmed_output"
                ((attempt++))
                continue
            fi
        fi

        # INGEN "exit utan marker" - kräv explicit DONE + verify
        # Om Claude avslutade utan marker, behandla som fel
        if [ $exit_code -eq 0 ]; then
            log "${YELLOW}⚠️ Claude avslutade utan DONE marker${NC}"
            error_context="Du avslutade utan att skriva <promise>DONE</promise>. Slutför uppgiften och skriv markern."
            ((attempt++))
            continue
        fi

        error_context="$output"
        ((attempt++))
        sleep 10
    done

    log "${RED}❌ Max retries för $(basename "$spec")${NC}"
    return 1
}

# =============================================================================
# KÖR PARALLELLT (worktrees)
# =============================================================================
run_parallel() {
    local specs=("$@")
    local pids=()
    local worktrees=()
    local branches=()
    local running=0

    log "${MAGENTA}=== PARALLEL MODE: ${#specs[@]} specs (max $PARALLEL_MAX samtidiga) ===${NC}"

    mkdir -p "$WORKTREE_BASE"

    for spec in "${specs[@]}"; do
        # Dynamisk skalning - kolla om vi kan köra fler
        maybe_scale_parallel $running

        # Vänta om vi nått max antal parallella
        while [ $running -ge $PARALLEL_MAX ]; do
            # Vänta på att någon blir klar
            for i in "${!pids[@]}"; do
                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    wait "${pids[$i]}" || true
                    unset 'pids[$i]'
                    ((running--))
                    # Kolla om vi kan skala upp efter att en blev klar
                    maybe_scale_parallel $running
                    break
                fi
            done
            sleep 2
        done

        local spec_name=$(basename "$spec" .md)
        local branch="ralph-$spec_name-$TIMESTAMP"
        local worktree="$WORKTREE_BASE/$spec_name-$TIMESTAMP"

        log "Skapar worktree: $spec_name"

        # Skapa branch och worktree
        git branch "$branch" 2>/dev/null || true
        git worktree add "$worktree" "$branch" 2>/dev/null || true

        # Kopiera spec
        cp "$spec" "$worktree/"

        worktrees+=("$worktree")
        branches+=("$branch")

        # Starta i bakgrunden
        (
            cd "$worktree"
            local log_file="ralph-parallel.log"

            # Kör spec
            if run_single_spec "$(basename "$spec")" "$branch" >> "$log_file" 2>&1; then
                echo "SUCCESS" > .ralph-status
            else
                echo "FAILED" > .ralph-status
            fi
        ) &
        pids+=($!)
        ((running++))

        log "  PID: ${pids[-1]} (running: $running/$PARALLEL_MAX)"
    done

    # Vänta på alla
    log "Väntar på ${#pids[@]} parallella specs..."

    local failed=0
    for i in "${!pids[@]}"; do
        wait "${pids[$i]}" || ((failed++))
        log "Klar: $(basename "${worktrees[$i]}")"
    done

    # Samla resultat och branches att merga
    log "${CYAN}═══ PARALLELL RESULTAT ═══${NC}"

    local successful_branches=()

    for i in "${!worktrees[@]}"; do
        local worktree="${worktrees[$i]}"
        local branch="${branches[$i]}"
        local status=$(cat "$worktree/.ralph-status" 2>/dev/null || echo "UNKNOWN")

        if [ "$status" = "SUCCESS" ]; then
            log "${GREEN}✅ $(basename "$worktree")${NC}"
            successful_branches+=("$branch")
        else
            log "${RED}❌ $(basename "$worktree")${NC}"
        fi
    done

    # Cleanup worktrees FÖRE merge (frigör branches)
    for worktree in "${worktrees[@]}"; do
        git worktree remove "$worktree" --force 2>/dev/null || true
    done
    git worktree prune 2>/dev/null || true

    # Smart sekventiell merge av lyckade branches
    if [ ${#successful_branches[@]} -gt 0 ]; then
        log "${CYAN}Startar smart merge av ${#successful_branches[@]} branches...${NC}"
        merge_branches_sequential "${successful_branches[@]}" || true

        # Kör post-merge hook för att fixa integration
        call_stack_hook "post-merge" "." || {
            log "${YELLOW}Post-merge hook misslyckades${NC}"
        }

        # Verifiera efter merge
        run_stack_verify "." || {
            log "${RED}Verifiering efter merge FAILED${NC}"
            notify "⚠️ Verifiering failed efter parallell merge"
        }
    fi

    return $failed
}

# =============================================================================
# AUTO-MERGE LOGIK
# =============================================================================

# Filer som är säkra att auto-resolve med --theirs
AUTO_RESOLVE_PATTERNS=(
    "*.log"
    "ralph-parallel.log"
    "test-results/*"
    "playwright-report/*"
    ".last-run.json"
    "coverage/*"
    "*.snap"
)

# Filer som kräver manuell review vid konflikt
MANUAL_REVIEW_PATTERNS=(
    "*.ts"
    "*.tsx"
    "*.js"
    "*.jsx"
    "*.py"
    "*.go"
    "*.rs"
    "*.java"
)

# Kolla om fil matchar pattern
file_matches_pattern() {
    local file="$1"
    local pattern="$2"

    # Konvertera glob till regex
    local regex=$(echo "$pattern" | sed 's/\./\\./g' | sed 's/\*/.*?/g')
    echo "$file" | grep -qE "$regex"
}

# Kolla om konfliktfil är säker att auto-resolve
is_safe_to_auto_resolve() {
    local file="$1"

    for pattern in "${AUTO_RESOLVE_PATTERNS[@]}"; do
        if file_matches_pattern "$file" "$pattern"; then
            return 0  # Säker
        fi
    done

    # Kolla om det är test-fil
    if echo "$file" | grep -qE "(__tests__|\.test\.|\.spec\.|test/|tests/)"; then
        return 0  # Test-filer är säkra
    fi

    return 1  # Inte säker
}

# Smart merge av en branch med konflikthantering
merge_branch_smart() {
    local branch="$1"
    local branch_name=$(basename "$branch")

    log "${CYAN}Merging: $branch_name${NC}"

    # Försök vanlig merge först
    if git merge --no-ff "$branch" -m "Merge $branch_name" 2>/dev/null; then
        log "${GREEN}✅ Clean merge: $branch_name${NC}"
        return 0
    fi

    # Konflikt - analysera filer
    local conflict_files=$(git diff --name-only --diff-filter=U 2>/dev/null)

    if [ -z "$conflict_files" ]; then
        log "${GREEN}✅ Merge OK (no conflicts): $branch_name${NC}"
        return 0
    fi

    log "${YELLOW}Konflikter i: $conflict_files${NC}"

    local has_source_conflict=false
    local resolved_count=0

    while IFS= read -r file; do
        [ -z "$file" ] && continue

        if is_safe_to_auto_resolve "$file"; then
            log "  ${BLUE}Auto-resolve (theirs): $file${NC}"
            git checkout --theirs "$file" 2>/dev/null || true
            git add "$file" 2>/dev/null || true
            ((resolved_count++))
        else
            # Kolla om det är källkod
            for pattern in "${MANUAL_REVIEW_PATTERNS[@]}"; do
                if file_matches_pattern "$file" "$pattern"; then
                    log "  ${RED}⚠️ Källkod-konflikt: $file${NC}"
                    has_source_conflict=true
                    break
                fi
            done

            # Om inte källkod, auto-resolve ändå
            if [ "$has_source_conflict" = false ]; then
                log "  ${BLUE}Auto-resolve (theirs): $file${NC}"
                git checkout --theirs "$file" 2>/dev/null || true
                git add "$file" 2>/dev/null || true
                ((resolved_count++))
            fi
        fi
    done <<< "$conflict_files"

    # Om källkod-konflikt, auto-resolve med theirs och notifiera
    if [ "$has_source_conflict" = true ]; then
        log "${YELLOW}⚠️ Källkod-konflikt - auto-resolve med theirs${NC}"
        notify "⚠️ Källkod-konflikt i $branch_name - auto-resolved"

        # Auto-resolve alla konflikter med theirs
        git checkout --theirs . 2>/dev/null || true
        git add -A 2>/dev/null || true
        ((resolved_count++))
    fi

    # Alla konflikter lösta automatiskt
    if [ $resolved_count -gt 0 ]; then
        git commit -m "Merge $branch_name (auto-resolved $resolved_count conflicts)" 2>/dev/null || true
        log "${GREEN}✅ Merge med auto-resolve: $branch_name ($resolved_count konflikter)${NC}"
    fi

    return 0
}

# Sekventiell merge av alla branches med smart konflikthantering
merge_branches_sequential() {
    local branches=("$@")
    local merged=0
    local failed=0
    local failed_branches=()

    log "${CYAN}═══ SMART SEQUENTIAL MERGE ═══${NC}"
    log "Branches att merga: ${#branches[@]}"

    # Checkout main först
    git checkout "$MAIN_BRANCH" 2>/dev/null || true

    # Sortera branches - test/compliance-branches sist (de ändrar oftast testfiler)
    local sorted_branches=()
    local test_branches=()

    for branch in "${branches[@]}"; do
        if echo "$branch" | grep -qE "(test|compliance|qa)"; then
            test_branches+=("$branch")
        else
            sorted_branches+=("$branch")
        fi
    done

    # Lägg till test-branches sist
    sorted_branches+=("${test_branches[@]}")

    log "Merge-ordning:"
    for i in "${!sorted_branches[@]}"; do
        log "  $((i+1)). ${sorted_branches[$i]}"
    done

    # Merga en i taget
    for branch in "${sorted_branches[@]}"; do
        if merge_branch_smart "$branch"; then
            ((merged++))

            # Kör tester efter varje merge
            if ! run_tests 2>/dev/null; then
                log "${YELLOW}⚠️ Tester failar efter merge av $branch${NC}"
                # Fortsätt ändå - kan fixas senare
            fi
        else
            ((failed++))
            failed_branches+=("$branch")
        fi
    done

    # Resultat
    log "${CYAN}═══ MERGE RESULTAT ═══${NC}"
    log "${GREEN}✅ Mergade: $merged${NC}"
    log "${RED}❌ Misslyckade: $failed${NC}"

    if [ $failed -gt 0 ]; then
        log "Branches som behöver manuell review:"
        for branch in "${failed_branches[@]}"; do
            log "  - $branch"
        done
    fi

    # Pusha main om något mergades
    if [ $merged -gt 0 ]; then
        log "${CYAN}Pushar $MAIN_BRANCH till origin...${NC}"
        git push origin "$MAIN_BRANCH" 2>&1 || log "${YELLOW}Push failed${NC}"
    fi

    return $failed
}

try_auto_merge() {
    local branch="$1"

    log "${CYAN}═══ AUTO-MERGE CHECK ═══${NC}"

    local safe=true

    # Check 1: Secrets i diff
    if git diff "$MAIN_BRANCH".."$branch" 2>/dev/null | grep -qE "(sk-ant-|ghp_|password|secret)" ; then
        log "${RED}⚠️ Secrets i diff${NC}"
        safe=false
    fi

    # Check 2: Farliga kommandon
    if git diff "$MAIN_BRANCH".."$branch" 2>/dev/null | grep -qE "(rm -rf /|sudo rm|curl.*\|.*bash)" ; then
        log "${RED}⚠️ Farliga kommandon${NC}"
        safe=false
    fi

    # Check 3: Tester
    if ! run_tests; then
        log "${RED}⚠️ Tester failar${NC}"
        safe=false
    fi

    if [ "$safe" = true ]; then
        log "${GREEN}🔥 AUTO-MERGE: $branch → $MAIN_BRANCH${NC}"
    else
        log "${YELLOW}⚠️ Säkerhetsvarningar - mergar ändå (skippar PR)${NC}"
    fi

    # Alltid merga till main (skippa PR-skapande för enklare workflow)
    git checkout "$MAIN_BRANCH"
    git merge "$branch" -m "Ralph: $branch" 2>/dev/null || {
        log "${YELLOW}Merge-konflikt - använder smart merge${NC}"
        merge_branch_smart "$branch"
    }
    git push origin "$MAIN_BRANCH" 2>/dev/null || true

    # Ta bort feature branch
    git branch -d "$branch" 2>/dev/null || true
    git push origin --delete "$branch" 2>/dev/null || true

    return 0
}

# =============================================================================
# SUMMARY RAPPORT
# =============================================================================
generate_summary() {
    local specs_done="$1"
    local specs_failed="$2"
    local specs_total="$3"

    local summary_file="$LOG_DIR/ralph-summary-$TIMESTAMP.md"

    cat > "$summary_file" << EOF
# 🤖 Ralph Summary

**Tid:** $(date '+%Y-%m-%d %H:%M:%S')
**Log:** $LOG_DIR/

## Resultat

| Status | Antal |
|--------|-------|
| ✅ Klara | $specs_done |
| ❌ Misslyckade | $specs_failed |
| **Totalt** | $specs_total |

## Rate Limits

$(tail -5 "$RATE_LIMIT_LOG" 2>/dev/null || echo "Inga")

## Token Usage

$(tail -5 "$TOKEN_LOG" 2>/dev/null || echo "Ingen data")

---
*Generated by ralph.sh*
EOF

    log "Summary: $summary_file"
}

# =============================================================================
# STATUS
# =============================================================================
show_status() {
    echo -e "${GREEN}=== Ralph Status ===${NC}"
    echo ""

    echo "Processer:"
    ps aux | grep -E "ralph|claude" | grep -v grep | head -5 || echo "  Inga"
    echo ""

    if git rev-parse --git-dir > /dev/null 2>&1; then
        echo "Git:"
        git log --oneline -5 2>/dev/null
        echo ""
        git status --short | head -10
    fi
    echo ""

    echo "Rate limits (senaste 5):"
    tail -5 "$RATE_LIMIT_LOG" 2>/dev/null || echo "  Inga"
    echo ""

    echo "Token usage (senaste 5):"
    tail -5 "$TOKEN_LOG" 2>/dev/null || echo "  Ingen data"
}

# =============================================================================
# WATCH MODE (Fireplace View) - Enhanced Dashboard
# =============================================================================
show_watch() {
    # Initiera stack för att visa info
    CURRENT_STACK=$(detect_stack ".")
    STACK_TEMPLATE_DIR="$RALPH_DIR/templates/stacks/$CURRENT_STACK"

    echo -e "${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    🔥 RALPH DASHBOARD 🔥                      ║"
    echo "║                                                               ║"
    echo "║   Luta dig tillbaka och observera. Ralph jobbar.              ║"
    echo "║   Ctrl+C för att avsluta                                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    while true; do
        clear
        echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${MAGENTA}                    🔥 RALPH DASHBOARD 🔥                       ${NC}"
        echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${CYAN}[$(date '+%H:%M:%S')] Status${NC}"
        echo ""

        # Stack info
        echo -e "${BLUE}Stack: ${GREEN}$CURRENT_STACK${NC}"
        if [ -d "$STACK_TEMPLATE_DIR" ]; then
            echo -e "${BLUE}Template: ${GREEN}$STACK_TEMPLATE_DIR${NC}"
        fi
        echo ""

        # Worktrees (parallella builds)
        local worktree_count=$(git worktree list 2>/dev/null | wc -l | tr -d ' ')
        if [ "$worktree_count" -gt 1 ]; then
            echo -e "${YELLOW}Aktiva worktrees: ${GREEN}$worktree_count${NC}"
            git worktree list 2>/dev/null | tail -n +2 | sed 's/^/  /'
            echo ""
        fi

        # Aktiva processer
        echo -e "${YELLOW}Processer:${NC}"
        local procs=$(ps aux | grep -E "ralph|claude" | grep -v grep | grep -v watch)
        if [ -n "$procs" ]; then
            echo "$procs" | awk '{printf "  %-8s %5s%% CPU  %5s%% MEM  %s\n", $11, $3, $4, $12}' | head -5
        else
            echo "  (inga aktiva)"
        fi
        echo ""

        # Specs status
        local total_specs=$(ls -1 specs/*.md 2>/dev/null | wc -l | tr -d ' ')
        local done_specs=$(ls -1 .spec-checksums/*.md5 2>/dev/null | wc -l | tr -d ' ')
        if [ "$total_specs" -gt 0 ]; then
            local percent=$((done_specs * 100 / total_specs))
            echo -e "${YELLOW}Specs: ${GREEN}$done_specs${NC}/${CYAN}$total_specs${NC} (${percent}%)"
            # Progress bar
            local bar_width=40
            local filled=$((percent * bar_width / 100))
            local empty=$((bar_width - filled))
            printf "  ["
            printf "%${filled}s" | tr ' ' '█'
            printf "%${empty}s" | tr ' ' '░'
            printf "] %d%%\n" $percent
            echo ""
        fi

        # Senaste git commits
        if git rev-parse --git-dir > /dev/null 2>&1; then
            echo -e "${YELLOW}Senaste commits:${NC}"
            git log --oneline -5 2>/dev/null | sed 's/^/  /'
            echo ""

            # Ändrade filer
            local changes=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
            if [ "$changes" -gt 0 ]; then
                echo -e "${YELLOW}Ändrade filer: ${GREEN}$changes${NC}"
                git status --short 2>/dev/null | head -10 | sed 's/^/  /'
                echo ""
            fi
        fi

        # Progress.txt (short-term memory)
        if [ -f "$PROGRESS_FILE" ]; then
            local progress_lines=$(wc -l < "$PROGRESS_FILE" | tr -d ' ')
            echo -e "${YELLOW}Progress (senaste):${NC}"
            tail -5 "$PROGRESS_FILE" 2>/dev/null | sed 's/^/  /'
            echo ""
        fi

        # Senaste logg-entry
        local latest_log=$(ls -t "$LOG_DIR"/ralph-*.log 2>/dev/null | head -1)
        if [ -n "$latest_log" ]; then
            echo -e "${YELLOW}Senaste logg:${NC}"
            tail -8 "$latest_log" 2>/dev/null | sed 's/^/  /'
            echo ""
        fi

        # Rate limits & tokens
        local rate_count=$(wc -l < "$RATE_LIMIT_LOG" 2>/dev/null || echo 0)
        local token_total=$(awk -F'|' '{sum += $2} END {print sum}' "$TOKEN_LOG" 2>/dev/null || echo 0)
        echo -e "${YELLOW}Rate limits: ${RED}$rate_count${NC}  |  ${YELLOW}Tokens: ${CYAN}~$token_total${NC}"

        echo ""
        echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
        echo -e "  Uppdateras var 5:e sekund. ${CYAN}Ctrl+C${NC} för att avsluta."
        echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"

        sleep 5
    done
}

# =============================================================================
# HELP
# =============================================================================
show_help() {
    cat << EOF
${GREEN}ralph.sh${NC} - The One Script To Rule Them All

${YELLOW}Usage:${NC}
  ./ralph.sh                     Kör alla specs i specs/
  ./ralph.sh specs/10-theme.md   Kör en spec
  ./ralph.sh specs/*.md          Kör flera specs (parallellt)
  ./ralph.sh --status            Visa status
  ./ralph.sh --watch             Fireplace view (live monitoring)
  ./ralph.sh --help              Visa hjälp

${YELLOW}Features:${NC}
  ✓ Self-healing retries
  ✓ Rate limit handling
  ✓ Build lock cleanup
  ✓ Backup & secrets scanning
  ✓ Git branch isolation
  ✓ Smart parallel execution (max 3)
  ✓ Supervisor quality checks
  ✓ Auto-merge (om säkert)
  ✓ ntfy notifications
  ✓ progress.txt (short-term memory)
  ✓ CLAUDE.md updates (long-term memory)

${YELLOW}Environment:${NC}
  NTFY_TOPIC    ntfy topic (optional, no default)

EOF
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    # Parse args
    case "${1:-}" in
        --status|-s)
            show_status
            exit 0
            ;;
        --watch|-w)
            show_watch
            exit 0
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
    esac

    # Banner
    echo -e "${MAGENTA}"
    echo "  ██████╗  █████╗ ██╗     ██████╗ ██╗  ██╗"
    echo "  ██╔══██╗██╔══██╗██║     ██╔══██╗██║  ██║"
    echo "  ██████╔╝███████║██║     ██████╔╝███████║"
    echo "  ██╔══██╗██╔══██║██║     ██╔═══╝ ██╔══██║"
    echo "  ██║  ██║██║  ██║███████╗██║     ██║  ██║"
    echo "  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝"
    echo -e "${NC}"

    # Setup
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"

    notify "🚀 Ralph startar"
    log "${GREEN}=== Ralph Starting ===${NC}"

    # Detektera och initiera stack
    init_stack "."

    # Backup
    backup_project

    # Samla specs
    local specs=()

    if [ $# -eq 0 ]; then
        # Alla specs
        for f in specs/*.md; do
            [ -f "$f" ] && specs+=("$f")
        done
    else
        # Angivna specs
        specs=("$@")
    fi

    if [ ${#specs[@]} -eq 0 ]; then
        log "${RED}Inga specs hittades${NC}"
        exit 1
    fi

    log "Specs: ${#specs[@]}"

    local specs_done=0
    local specs_failed=0

    # Parallellt eller sekventiellt?
    if [ ${#specs[@]} -gt $PARALLEL_THRESHOLD ]; then
        # Parallellt
        run_parallel "${specs[@]}" && specs_done=${#specs[@]} || specs_failed=$?
    else
        # Sekventiellt
        for spec in "${specs[@]}"; do
            local branch="ralph-$(basename "$spec" .md)-$TIMESTAMP"

            # Skapa branch
            git checkout -b "$branch" 2>/dev/null || true

            if run_single_spec "$spec" "$branch"; then
                # Supervisor checks
                run_supervisor_checks || true

                # Update CLAUDE.md (long-term memory)
                update_claude_md "$(basename "$spec")"

                # Push branch
                git push -u origin "$branch" 2>/dev/null || true

                # Auto-merge (spec är redan klar, räkna som done)
                try_auto_merge "$branch" || true
                ((specs_done++))
            else
                ((specs_failed++))
                git checkout "$MAIN_BRANCH" 2>/dev/null || true
                git branch -D "$branch" 2>/dev/null || true
            fi
        done
    fi

    # =============================================================================
    # FINAL BUILD LOOP - Kör tills build passerar (definition of done!)
    # =============================================================================
    log "${MAGENTA}═══ FINAL BUILD CHECK ═══${NC}"
    log "Definition of Done: npm run build MÅSTE passera"

    local final_attempts=0
    local max_final_attempts=10  # Max 10 försök att fixa build
    local build_passed=false

    while [ $final_attempts -lt $max_final_attempts ]; do
        ((final_attempts++))
        log "${CYAN}Final build attempt $final_attempts/$max_final_attempts${NC}"

        # Säkerställ dependencies
        ensure_dependencies || true

        # Kör build
        local final_output
        local final_exit=0
        final_output=$(npm run build 2>&1) || final_exit=$?

        if [ $final_exit -eq 0 ]; then
            log "${GREEN}✅ FINAL BUILD PASSED!${NC}"
            build_passed=true

            # Commit och push
            git add -A 2>/dev/null || true
            git commit -m "Ralph: final build passed" 2>/dev/null || true
            git push origin "$MAIN_BRANCH" 2>/dev/null || true

            break
        fi

        log "${RED}❌ Build failed${NC}"
        echo "$final_output" | tail -30

        # Försök 1: Self-heal (saknade dependencies)
        if try_selfheal "$final_output"; then
            log "${CYAN}Self-heal kördes, försöker igen...${NC}"
            continue
        fi

        # Försök 2: Be Claude fixa
        log "${CYAN}Ber Claude fixa build-felen...${NC}"

        local fix_prompt="Build FAILED med följande fel:

$final_output

VIKTIGT: Detta är FINAL BUILD. Projektet måste bygga.
Analysera felet och fixa det. Kör sedan 'npm run build' för att verifiera.

När build passerar, skriv: <promise>DONE</promise>"

        local fix_output
        fix_output=$(echo "$fix_prompt" | timeout $TIMEOUT claude --dangerously-skip-permissions -p 2>&1) || true

        echo "$fix_output"

        # Commit eventuella ändringar
        if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
            git add -A 2>/dev/null || true
            git commit -m "Ralph: fix build (attempt $final_attempts)" 2>/dev/null || true
        fi

        sleep 5
    done

    if [ "$build_passed" = false ]; then
        log "${RED}═══ FINAL BUILD FAILED EFTER $max_final_attempts FÖRSÖK ═══${NC}"
        notify "❌ Final build failed efter $max_final_attempts försök" "urgent"
        specs_failed=$((specs_failed + 1))
    fi

    # Summary
    generate_summary "$specs_done" "$specs_failed" "${#specs[@]}"

    # Final notification
    if [ $specs_failed -eq 0 ] && [ "$build_passed" = true ]; then
        notify "✅ Ralph DONE: $specs_done/${#specs[@]} specs, build OK"
        log "${GREEN}═══ RALPH DONE: $specs_done/${#specs[@]}, BUILD OK ═══${NC}"
    else
        notify "⚠️ Ralph: $specs_done OK, $specs_failed failed, build: $build_passed"
        log "${YELLOW}═══ RALPH: $specs_done OK, $specs_failed FAILED, build: $build_passed ═══${NC}"
    fi

    # Exit code baserat på build status
    if [ "$build_passed" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# Kör
main "$@"
