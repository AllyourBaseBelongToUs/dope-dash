# 🚀 SUPER DUPER PLAN - Ralph Inferno Monitoring Dashboard

**Date Created:** 2026-01-23
**Status:** Ready for Implementation
**Timeline:** 4 weeks (MVP in Week 1)
**AOT Session:** 2025-01-23 decomposition

---

## 📊 Executive Summary

**Vision:** A unified web dashboard that monitors and controls multiple autonomous agent sessions (Ralph, Claude Code, Cursor, Terminal, IDEs) on your VM, accessible from Windows with real-time updates, intervention capabilities, database-first persistence, and dual-mode communication.

**Timeline:** 4 weeks (MVP in Week 1, production-ready by Week 4)

**Architecture:** VM-based Python backend + Next.js frontend + PostgreSQL database-first persistence

**User Enhancements Integrated:**
- ✅ Command execution (UI controls + slash commands)
- ✅ Dual-mode intervention (quick actions + custom feedback with timeout)
- ✅ Polling/WebSocket hybrid (toggle between real-time and on-demand)
- ✅ Database-first storage (PostgreSQL as source of truth)
- ✅ Extended retention (30 days events, 1 year sessions, SQL is cheap!)
- ✅ Multi-agent control (Ralph + Claude + Cursor + Terminal + IDEs)
- ✅ Enhanced analytics (real-time metrics + on-demand history rebuild)
- ✅ Audio + deployment notifications (both toggleable)

---

## 🎯 What You're Getting

| Week | Capability | Example |
|------|------------|---------|
| **1** | **Real-time monitoring** | "3 of 11 specs complete, currently running: CR-02" |
| **2** | **Control & intervention** | Pause, skip, or stop specs from browser + slash commands |
| **3** | **Multi-agent + Claude Code** | Control Ralph, Claude, Cursor, Terminal from one dashboard |
| **4** | **Production automation** | PDF reports, audio alerts, database-first analytics, set-and-forget |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Windows Machine                        │
├─────────────────────────────────────────────────────────────────┤
│  Browser: http://192.168.206.128:8003/dashboard               │
│  ├─ Real-time progress (WebSocket push OR polling)            │
│  ├─ Control buttons (pause/resume/skip)                        │
│  ├─ Command palette (Ctrl+K: slash commands)                   │
│  ├─ Custom feedback textarea (with timeout countdown)          │
│  ├─ Multi-agent monitor (Ralph + Claude + Cursor + Terminal)  │
│  ├─ Connection mode toggle (WebSocket/Polling)                 │
│  ├─ Notification toggles (audio/deployment alerts)             │
│  └─ Analytics panel (real-time + on-demand history)            │
└─────────────────────────────────────────────────────────────────┘
                    ↕ HTTPS/WebSocket/Polling
┌─────────────────────────────────────────────────────────────────┐
│                       VM (192.168.206.128)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  All Agent Sessions (unified interface)                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Ralph Sessions (tmux)                                 │      │
│  │   - nonprofit-matcher (3/11 specs)                    │      │
│  │   - project-alpha (CR-02 running)                     │      │
│  │                                                        │      │
│  │ Claude Code Sessions (CLI wrappers)                    │      │
│  │   - claude-abc123 (gemini-1.5-flash)                  │      │
│  │   - claude-def456 (claude-opus-4.5)                   │      │
│  │                                                        │      │
│  │ Cursor Sessions (tmux)                                 │      │
│  │   - cursor-main (coding agent-x)                      │      │
│  │                                                        │      │
│  │ Terminal Sessions (tmux)                               │      │
│  │   - ralph-main (1 window)                              │      │
│  │   - debug-server (build running)                       │      │
│  │                                                        │      │
│  │ IDE Sessions (Future: VS Code MCP)                     │      │
│  └──────────────────────────────────────────────────────┘      │
│                         │                                      │
│                         │ Event Capture (all agents)          │
│                         ▼                                      │
│  Monitoring Infrastructure (0.0.0.0:8001-8004)                    │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Port 8001: WebSocket Server (FastAPI)                │      │
│  │   - Receives events from all agents                   │      │
│  │   - Broadcasts to dashboard (push mode)               │      │
│  │   - Accepts intervention commands                     │      │
│  ├──────────────────────────────────────────────────────┤      │
│  │ Port 8002: Control API (FastAPI)                      │      │
│  │   - Ralph control commands                            │      │
│  │   - Claude wrapper (stdin/stdout)                     │      │
│  │   - Cursor wrapper (stdin/stdout)                     │      │
│  │   - Terminal tmux send-keys                           │      │
│  ├──────────────────────────────────────────────────────┤      │
│  │ Port 8003: Dashboard (Next.js)                        │      │
│  │   - React UI with dual-mode communication             │      │
│  │   - WebSocket client OR polling client                │      │
│  │   - Command palette (Ctrl+K)                          │      │
│  │   - Multi-agent session viewer                        │      │
│  ├──────────────────────────────────────────────────────┤      │
│  │ Port 8004: Analytics API (FastAPI)                    │      │
│  │   - Session history queries                           │      │
│  │   - On-demand analytics rebuild                       │      │
│  │   - Cost/trend aggregation                            │      │
│  └──────────────────────────────────────────────────────┘      │
│                         │                                      │
│                         ▼                                      │
│  PostgreSQL (localhost:5432) - DATABASE FIRST                   │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ ralph_monitoring database                              │      │
│  │                                                        │      │
│  │ events (source of truth)                              │      │
│  │   - Every event stored immediately                    │      │
│  │   - spec_started, spec_completed, spec_failed         │      │
│  │   - intervention_request, timeout_triggered           │      │
│  │   - session_heartbeat, user_feedback                  │      │
│  │   - Retention: 30 days                                │      │
│  │                                                        │      │
│  │ sessions (aggregates)                                  │      │
│  │   - Session groups (overnight runs)                   │      │
│  │   - Start/end timestamps, total specs                 │      │
│  │   - Final result, cost summary                        │      │
│  │   - Retention: 1 year                                 │      │
│  │                                                        │      │
│  │ spec_runs (individual executions)                     │      │
│  │   - Per-spec duration, success/failure                │      │
│  │   - Token usage, error details                         │      │
│  │   - Retention: 1 year                                 │      │
│  │                                                        │      │
│  │ metric_buckets (pre-aggregated)                       │      │
│  │   - Real-time dashboard numbers                        │      │
│  │   - 5-minute buckets                                  │      │
│  │   - Retention: 7 days                                 │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Principles:**
1. **Database-First:** PostgreSQL is source of truth, NOT in-memory
2. **Dual-Mode Communication:** WebSocket (real-time) OR polling (on-demand)
3. **Unified Session Model:** Single interface for all agent types
4. **Event-Driven:** All events stored immediately, then pushed/notified
5. **Extended Retention:** 30 days events, 1 year sessions (SQL is cheap!)

---

## 🔌 Port Architecture (Zero Conflicts)

| Port Range | Purpose | Binding | Access From |
|------------|---------|---------|-------------|
| **3000-3099** | Dev servers | `127.0.0.1` (localhost) | SSH tunnel only |
| **8001** | WebSocket (real-time push) | `0.0.0.0` (all interfaces) | Windows: `192.168.206.128:8001` |
| **8002** | Control API (all agents) | `0.0.0.0` (all interfaces) | Windows: `192.168.206.128:8002` |
| **8003** | Dashboard (Next.js) | `0.0.0.0` (all interfaces) | Windows: `http://192.168.206.128:8003` |
| **8004** | Analytics API (on-demand) | `0.0.0.0` (all interfaces) | Windows: `192.168.206.128:8004` |
| **5432** | PostgreSQL | `127.0.0.1` (localhost) | Local only |

**Why This Works:**
- Dev servers bind to localhost → can't conflict with monitoring ports
- Monitoring binds to explicit IP `0.0.0.0` → accessible from Windows
- Different ranges (3000s vs 8000s) → impossible to confuse

---

## 🎛️ Unified Control Interface (Query + Execution + Hotkeys + Buttons + Tapper)

### Three Input Methods, One Unified System

The dashboard supports **multiple ways to control agents**, all routing to the same backend:

```
┌─────────────────────────────────────────────────────────────┐
│  Input Methods                                                │
├─────────────────────────────────────────────────────────────┤
│  1. Clickable Buttons (Mouse)                                 │
│     - Quick actions: Pause, Resume, Skip, Stop              │
│     - Agent selector: Ralph, Claude, Cursor, Terminal       │
│     - Command builder with autocomplete                      │
│                                                              │
│  2. Hotkeys (Keyboard)                                       │
│     - Ctrl+K: Command palette                                │
│     - Ctrl+Shift+P: Pause                                    │
│     - Ctrl+1-4: Switch agent focus                           │
│                                                              │
│  3. Slash Commands (Text)                                    │
│     - /pause, /status, /commit, etc.                        │
│     - Text blocks: "design-check http://localhost:3000"     │
│     - Macros: /deploy-full expands to saved commands        │
│                                                              │
│  4. Tapper Device (Hardware - Future)                        │
│     - Physical buttons mapped to commands                   │
│     - LED feedback shows agent status                        │
│     - Context-aware (changes per agent)                     │
└─────────────────────────────────────────────────────────────┘
```

---

### 📋 Command Modes: Query vs Execution

All commands route through the **same infrastructure**, but have different intent:

#### Query Mode (Ask Agent About Itself)

Commands that **request information FROM** the agent:

```bash
/status                  → "What are you working on?"
/tokens                  → "Token usage?"
/logs                    → "Show logs"
/eta                     → "Time remaining?"
/ask "Why did it fail?"  → Query the agent
```

**How it works:**
```python
# Query mode - parse and display structured response
response = send_to_agent(current_agent, "What are you working on?")
parsed = parse_agent_response(response)
display_to_dashboard(parsed)
```

#### Execution Mode (Send Command to Agent to Run)

Commands that **trigger actions INSIDE** the agent:

```bash
# Ralph control
/pause                   → Pauses Ralph execution
/skip                    → Skips current spec
/stop                    → Stops Ralph

# Claude/Cursor commands (sent to agent via stdin/tmux)
/commit                  → Triggers Claude's commit skill
/review-pr               → Triggers PR review skill
/retry                   → Retries current task

# Skill invocations (sent as text)
"design-check http://localhost:3000"  → Runs design-check skill
"use test-runner for this task"        → Invokes test-runner agent
"run the e2e tests now"                → Natural language command
```

**How it works:**
```python
# Execution mode - send command, show raw output
response = send_to_agent(current_agent, "/commit")
display_raw_output(response)  # Agent processes natively
```

**Same Infrastructure:**
```python
async def send_to_agent(agent_type: str, instruction: str):
    """Unified command router for all agent types"""

    if agent_type == 'ralph':
        # tmux send-keys
        subprocess.run(['tmux', 'send-keys', '-t', 'ralph', instruction, 'Enter'])
        return capture_tmux_output('ralph')

    elif agent_type == 'claude':
        # stdin wrapper
        process = claude_sessions[session_id]
        process.stdin.write(instruction + '\n')
        process.stdin.flush()
        return await read_process_output(process)

    elif agent_type == 'cursor':
        # tmux send-keys (Cursor runs in tmux)
        subprocess.run(['tmux', 'send-keys', '-t', cursor_session, instruction, 'Enter'])
        return capture_tmux_output(cursor_session)
```

---

### ⌨️ Essential Hotkeys (Simplified)

**Only the essential hotkeys** - everything else is a button click:

```
┌─────────────────────────────────────────────────────────────┐
│  Essential Hotkeys                                           │
├─────────────────────────────────────────────────────────────┤
│  Ctrl+K              - Command palette (search anything)      │
│  Ctrl+1              - Switch to Ralph                       │
│  Ctrl+2              - Switch to Claude                      │
│  Ctrl+3              - Switch to Cursor                      │
│  Ctrl+4              - Switch to Terminal                    │
│  Ctrl+Tab            - Cycle through agents                   │
│  Escape              - Close modal/drawer                    │
│                                                              │
│  That's it. Only 7 hotkeys.                                │
│  Everything else? Click a button.                           │
└─────────────────────────────────────────────────────────────┘
```

**Why so few?**
- Buttons are easier to remember
- Clickable buttons show what they do
- Hotkeys for power users only
- Don't overwhelm users

---

### 🖱️ Clickable Buttons (Primary Interface)

**Buttons ARE the hotkeys** - click them, they send commands:

```
┌─────────────────────────────────────────────────────────────┐
│  Quick Actions Bar (Always Visible)                           │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  /pause   │ │  /resume  │ │  /skip    │ │  /stop    │  │
│  │           │ │           │ │           │ │           │  │
│  │ ⏸  Pause │ │ ▶ Resume  │ │ ⏭  Skip   │ │ ⏹  Stop   │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │ /commit   │ │ /review   │ │design-    │ │  /status  │  │
│  │           │ │           │ │check      │ │           │  │
│  │ 📋 Commit │ │ 🔍 Review │ │ 🎨 Check  │ │ 📊 Status │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │run-e2e    │ │deploy     │ │build-all  │ │/analytics │  │
│  │           │ │           │ │           │ │           │  │
│  │ 🧪 Test   │ │ 🚀 Deploy │ │ 🔨 Build  │ │ 📈 Analyze│  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                              │
│  Agent Selector:                                             │
│  [Ralph ▼] [Claude] [Cursor] [Terminal]                       │
│                                                              │
│  Each button shows:                                          │
│  - Command/skill name                                        │
│  - Icon for visual recognition                               │
│  - Hover tooltip with details                                │
└─────────────────────────────────────────────────────────────┘
```

**Button Categories:**
1. **Quick Actions** - Pause, Resume, Skip, Stop
2. **Agent Commands** - Commit, Review, Status
3. **Skills** - Design-check, E2E tests, Deploy, Build
4. **Agent Selector** - Switch between Ralph/Claude/Cursor/Terminal
5. **Saved Commands** - User-defined macros (add your own!)

**How It Works:**
- Click button → Sends slash command/skill to agent
- Hover button → Animated tooltip shows what it does
- Right-click → Edit button or add to quick actions

---

### 🔍 Kickass Command Palette (Ctrl+K)

**The star of the show** - search, filter, scroll, animated tooltips:

```
┌─────────────────────────────────────────────────────────────┐
│  >                                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Commands                                    Filter...   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Matching Commands (filter as you type):                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ /pause                              Pause agent     │  │
│  │    ⏸ Pauses the current agent at next safe point     │  │
│  │                                                        │  │
│  │ /resume                             Resume agent    │  │
│  │    ▶ Continues paused agent execution               │  │
│  │                                                        │  │
│  │ /commit                             Git commit       │  │
│  │    📋 Trigger Claude's commit skill                  │  │
│  │                                                        │  │
│  │ design-check                        Design skill     │  │
│  │    🎨 Run design-check skill on URL (prompt for URL)│  │
│  │                                                        │  │
│  │ run-e2e                             E2E tests        │  │
│  │    🧪 Run full E2E test suite                       │  │
│  │                                                        │  │
│  │ deploy-full                         Deploy macro     │  │
│  │    🚀 Build, test, commit, push (saved macro)     │  │
│  │                                                        │  │
│  │ [scroll down for more...]                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Keyboard: [↑↓] navigate  [Enter] execute  [Esc] close      │
│  Mouse: Scroll to browse, Click to select                   │
│                                                              │
│  Hover any command → Animated tooltip appears:              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ /pause - Pauses the current agent execution         │  │
│  │                                                        │  │
│  │ Usage: Press Ctrl+Shift+P or click Pause button       │  │
│  │ Agent: Ralph, Claude, Cursor, Terminal                │  │
│  │ Example: "Pauses Ralph at CR-02 before continuing"    │  │
│  │                                                        │  │
│  │ [fade in animation]                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
1. **Instant Search** - Type any command/skill name, filters instantly
2. **Mouse Scroll** - Browse all commands with mouse wheel
3. **Keyboard Nav** - Arrow keys + Enter to execute
4. **Animated Tooltips** - Hover shows:
   - What the command does
   - Which agents it works with
   - Example usage
   - Related commands
   - Fade-in animation (smooth!)

**Command Categories:**
- **Agent Control** - /pause, /resume, /skip, /stop
- **Queries** - /status, /tokens, /logs, /eta
- **Claude Skills** - /commit, /review, /refactor
- **Custom Skills** - design-check, e2e-test, deploy
- **Macros** - saved command sequences
- **Dashboard** - /analytics, /settings, /help

**Smart Filtering:**
```
Type "test" → Shows:
- /run-e2e
- /test-unit
- test-deploy macro
- Any command with "test" in name

Type "claude" → Shows:
- /commit (Claude only)
- /review (Claude only)
- All Claude-specific commands
```

**Why This Is Awesome:**
- Discoverable - see ALL commands in one place
- Fast - type to filter, click to execute
- Beautiful - smooth animations, hover effects
- Smart - learns which commands you use, shows first
- Accessible - keyboard OR mouse, your choice

---

### 💬 Dashboard Slash Commands (Meta-Commands)

Slash commands **inside the dashboard** that trigger actions or send to agents:

```
// Agent Control Commands
/pause [agent]              - Pause agent (default: current)
/resume [agent]             - Resume agent
/skip [agent]               - Skip current task
/stop [agent]               - Stop agent
/restart [agent]            - Restart agent

// Query Commands
/status [agent]              - Show agent status
/tokens [agent]             - Show token usage
/logs [agent]               - Show logs
/eta [agent]                - Show time remaining

// Execution Commands (send to agent)
/run <command>              - Send command to agent
/skill <skill-name> <args>   - Invoke skill
/commit                    - Trigger commit (Claude)
/review                    - Trigger review (Claude)

// Dashboard Commands
/switch <agent>             - Switch active agent
/focus <agent>              - Focus on specific agent
/split <agent1> <agent2>    - Split view between agents

// Text Block Commands
/template <name>            - Insert text template
/macro <name>               - Execute saved macro
/paste <name>               - Paste saved text
/run-script <name>          - Open editor → Save → Send to agent

// Analytics Commands
/analytics                  - Open analytics panel
/rebuild                    - Rebuild analytics
/export <format>            - Export data (csv/json)

// Settings Commands
/settings                   - Open settings
/hotkeys                    - Show hotkey reference
/help                       - Show all commands
```

### Text Block Triggers

**Multi-line scripts sent to agents:**

```bash
// Opens editor, saves script, sends to agent
/run-script my-deploy-script

→ Opens text editor in dashboard
→ User types/pastes multi-line script:
   cd ~/projects/nonprofit-matcher
   npm run build
   npm run test
   if [ $? -eq 0 ]; then
     echo "Build successful"
   fi
→ Save
→ Script sent to agent to execute
```

### Macro System

**Save and replay complex commands:**

```bash
// Define macro
/macro-save deploy-full
→ Opens editor
→ User types: "cd ~/projects/nonprofit-matcher && npm run build && npm run test"
→ Saves as "deploy-full"

// Later, just type
/deploy-full
→ Expands to full command
→ Sends to agent
```

---

### 🎹 Future Vision: Hardware Tapper Device Integration

**Ultimate vision:** Physical tapper device with symbols that trigger commands/skills/states

```
┌─────────────────────────────────────────────────────────────┐
│  Tapper Device Architecture (Future)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Hardware Device (USB/MIDI/Bluetooth)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [Symbol 1] [Symbol 2] [Symbol 3] [Symbol 4]        │  │
│  │ [Symbol 5] [Symbol 6] [Symbol 7] [Symbol 8]        │  │
│  │ [Symbol 9] [Symbol 10] [Symbol 11] [Symbol 12]      │  │
│  │ [Symbol 13] [Symbol 14] [Symbol 15] [Symbol 16]    │  │
│  │          (LED feedback under each symbol)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                  │
│                         ▼                                  │
│  WebHID API / WebMIDI API (Browser)                         │
│                         │                                  │
│                         ▼                                  │
│  Dashboard Tapper Mapping Layer                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Symbol → Action Mapping                               │  │
│  │                                                        │  │
│  │ Symbol 1 → /pause (current agent)                    │  │
│  │ Symbol 2 → /resume                                    │  │
│  │ Symbol 3 → /skip                                      │  │
│  │ Symbol 4 → "design-check http://localhost:3000"      │  │
│  │ Symbol 5 → /commit                                    │  │
│  │ Symbol 6 → /review-pr                                 │  │
│  │ Symbol 7 → Switch to Ralph                            │  │
│  │ Symbol 8 → Switch to Claude                           │  │
│  │ Symbol 9 → Mute notifications                          │  │
│  │ Symbol 10 → Rebuild analytics                          │  │
│  │                                                        │  │
│  │ Modifiers:                                            │  │
│  │ - Shift + Symbol = Secondary action                   │  │
│  │ - Hold Symbol = Continuous mode                        │  │
│  │ - Double tap = Alternative action                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                  │
│                         ▼                                  │
│  Command Router                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Detect target agent → Send command                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  UI: Tapper Configuration Panel                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [Symbol 1] → [Action ▼] [Edit Text]                  │  │
│  │ [Symbol 2] → [Action ▼] [Edit Text]                  │  │
│  │                                                        │  │
│  │ Presets:                                               │  │
│  │ [Ralph Control] [Claude Dev] [Testing] [Deployment]  │  │
│  │                                                        │  │
│  │ [Learn Mode] - Tap symbol, then perform action       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Symbol Categories & LED Feedback

**LED States (under each symbol):**
- 🟢 Green idle = Agent running normally
- 🟡 Yellow idle = Agent waiting for input
- 🔴 Red idle = Agent error
- 💫 Blinking = Action in progress

**Context Switching:**
- **Tap symbol** → Quick action
- **Hold symbol** → Switch context (agent focus)
- **Double tap** → Open options menu

#### Example Use Cases

**Development Preset:**
```
Symbol 1: /pause (current agent)
Symbol 2: /commit (Claude)
Symbol 3: "design-check http://localhost:3000"
Symbol 4: /run-e2e-tests
Symbol 5: /rebuild-analytics
Symbol 6: Switch to Ralph
Symbol 7: Switch to Claude
Symbol 8: Mute notifications
```

**Deployment Preset:**
```
Symbol 1: "npm run build"
Symbol 2: "npm run test"
Symbol 3: /commit "Deploy: $(date)"
Symbol 4: git push
Symbol 5: /deploy-to-staging
Symbol 6: /run-smoke-tests
```

#### Hardware Options

**Potential Devices:**
1. **Stream Deck** (15 LCD keys, programmable) - $150
2. **Macropad** (Mechanical keys, QMK programmable) - $50-100
3. **MIDI Controller** (Pads, knobs, sliders) - $100-300
4. **Custom Tapper** (DIY with Arduino/ESP32) - $20-50
5. **Touch OSC** (iPad app with customizable buttons) - $5

**Integration APIs:**
- **WebHID API** - USB device communication
- **WebMIDI API** - MIDI controller support
- **WebSocket Bridge** - For non-web devices

#### Learn Mode

```
1. Click [Learn Mode] in dashboard
2. Tap symbol on tapper device
3. Perform action (type command, click button, etc.)
4. Dashboard learns mapping
5. Symbol now triggers that action
```

---

### NOT Using Skills Injection

**Why NOT skills injection?**
- Overkill for simple pause/skip commands
- Skills system is complex (format, injection, lifecycle)
- This unified interface gives same benefit with less complexity
- UI controls are more discoverable than injected skills

**How skills ARE invoked:**
- User types: `"design-check http://localhost:3000"`
- Dashboard sends to Claude/Cursor as text input
- Agent processes the skill invocation natively
- No injection needed - just text communication

---

## 🔄 Dual-Mode Intervention System

### Auto-Detection Based on User Action

**No Explicit Toggle - Smart Defaults**

```
┌─────────────────────────────────────────────────────────────┐
│  Controls & Feedback                                        │
├─────────────────────────────────────────────────────────────┤
│  Quick Actions (Buttons)                                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ ⏸ Pause │  │ ▶ Resume│  │ ⏭ Skip  │  │ ⏹ Stop  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                              │
│  OR                                                           │
│                                                              │
│  Custom Instruction (Textarea with Timeout)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Type custom instruction for Ralph...                 │  │
│  │                                                      │  │
│  │ Auto-send in: 15s (typing resets timer) [Send]     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Mode Detection Logic

```typescript
// Mode is determined by user action, NOT explicit toggle
if (userClicksButton) {
  mode = 'QUICK';
  action = buttonAction;
  sendImmediately();
} else if (userTypesInTextarea) {
  mode = 'CUSTOM';
  if (userClicksSend) {
    sendCustomInstruction();
  } else if (timeoutExpires) {
    discardText();
    executeDefaultAction();  // Configurable: continue/abort/pause
  }
}
```

### Smart Timeout Behavior

- **Default timeout:** 30 seconds (configurable)
- **Typing resets timer:** Any keypress extends timeout
- **Visual countdown:** Shows remaining time
- **Configurable default action:** Continue/Abort/Pause when timeout expires
- **Discard text:** If user abandons, text is discarded

### User Feedback Benefits

- **Quick mode:** One-click actions for common operations
- **Custom mode:** Natural language instructions for complex scenarios
- **No mode confusion:** Auto-detection based on action
- **Flexible timeout:** Can be disabled or extended
- **Always available:** Both modes coexist, user chooses implicitly

---

## 📡 Polling + WebSocket Hybrid (User Toggle)

### Two Communication Modes

#### Mode 1: WebSocket (Real-Time Push)
- **When to use:** Actively monitoring, overnight builds with screen on
- **Behavior:** Server pushes updates immediately when events occur
- **Pros:** Real-time, low latency, efficient
- **Cons:** Requires persistent connection, breaks if network hiccups

#### Mode 2: Polling (On-Demand)
- **When to use:** Checking progress sporadically, connection unstable
- **Behavior:** Dashboard queries database every N seconds
- **Pros:** Works even if connection drops, simple, reliable
- **Cons:** Delayed updates (up to N seconds old), more server load

### Toggle UI

```
┌─────────────────────────────────────────────────────────────┐
│  Connection Mode                                    ●    │
│  ◉ Real-time (WebSocket)                                    │
│  ○ On-demand (Polling)                                    │
├─────────────────────────────────────────────────────────────┤
│  Current mode: Real-time                                    │
│  Update frequency: Push on event                           │
│  Last update: 2 seconds ago                                 │
└─────────────────────────────────────────────────────────────┘
```

### Connection Status Badges

```
● Live (green, pulsing)       - WebSocket connected, receiving real-time updates
● Delayed (yellow)            - Polling mode, shows delay in seconds
● Offline (gray)              - Disconnected, shows last update time
```

### Use Cases

**Overnight Monitoring (WebSocket Mode):**
- Start Ralph at 10pm, keep dashboard open on tablet
- Dashboard receives push updates all night
- "Live" indicator (green, pulsing)
- Zero delay when events occur

**Sporadic Checking (Polling Mode):**
- At work, check Ralph progress occasionally during coffee breaks
- Dashboard queries database every 10s
- "Last update: 15 seconds ago" indicator
- Saves battery (no persistent connection)

**Unreliable Network (Automatic Fallback):**
- Internet connection drops periodically
- Dashboard detects connection dropped
- Automatically switches to polling mode
- Shows yellow badge: "Delayed mode (polling every 10s)"
- When connection restored, asks: "Switch back to real-time?"

### Database as Source of Truth

**Key insight:** Both modes read from the SAME database
- All events stored in PostgreSQL immediately
- WebSocket pushes events (for real-time)
- Polling queries database (for on-demand)
- Either way: Same data, just different delivery mechanism
- No progress lost regardless of connection mode

---

## 🗄️ Database-First Architecture (Enhanced Retention)

### Why Database-First?

**User's Key Requirement:**
> "we defintly want the database tooooo, especially for times where we sleep or are away and the agents do their shenanigans we wnana know exactly what happened"

**Translation:** Database is non-negotiable. We want to know EXACTLY what happened, even when we're asleep.

### Storage Hierarchy

```
PostgreSQL (VM) - Source of Truth
│
├─ events (source of truth)
│   - Every event stored with timestamp
│   - spec_started, spec_completed, spec_failed
│   - intervention_request, timeout_triggered
│   - session_heartbeat, user_feedback
│   - All with full context (JSON metadata)
│   - Retention: 30 days
│
├─ sessions (aggregates)
│   - Session groups (overnight runs)
│   - Start/end timestamps, total specs
│   - Final result, cost summary
│   - Retention: 1 year
│
├─ spec_runs (individual executions)
│   - Per-spec duration, success/failure
│   - Token usage, error details
│   - Retention: 1 year
│
└─ metric_buckets (pre-computed)
    - Real-time dashboard numbers
    - Hourly/daily aggregates
    - Retention: 7 days
```

### Extended Retention Policy

**User asked:** "we would like more than just 72 hours history if we want (guess SQL database space is cheap?)"

**Answer:** YES! SQL is cheap.

| Data Type | Retention | Rationale |
|-----------|-----------|------------|
| **Events** | 30 days | Debugging recent issues |
| **Sessions** | 1 year | Long-term trend analysis |
| **Spec Runs** | 1 year | Performance tracking |
| **Metric Buckets** | 7 days | Dashboard performance (temporary) |

**Why 1 year for sessions/specs?**
- Long-term trends: "Is performance improving over months?"
- Seasonal patterns: "Do certain specs fail more in winter?"
- Cost tracking: "What's our monthly Claude bill?"

**For longer retention:** Export to external storage (S3, local archives)

### Event Capture Pipeline

```
Ralph/Claude Agent
    ↓ (does something)
[Event Emitted]
    ↓
[PostgreSQL INSERT] ← IMMEDIATE write, no buffering
    ↓
[Persisted to disk]
    ↓
[WebSocket Notification] → Dashboard (if connected)
    ↓
[Database Query] ← Dashboard (polling or on-demand)
```

### Key Principle

**Database writes are IMMEDIATE and PERMANENT.**
- Event occurs → INSERT into events table
- This happens BEFORE WebSocket push
- This happens BEFORE dashboard poll
- Database is source of truth

**Dashboard can always retrieve latest state:**
- WebSocket: Gets pushed events (fast)
- Polling: Queries database (slower but reliable)
- Either way: Same data from database

### Benefits

1. **No Data Loss** - Everything stored immediately to PostgreSQL
2. **True History & Analytics** - Query "What happened last night?"
3. **Multiple Clients Support** - Dashboard, CLI tool, mobile app all read from same source
4. **Audit & Debugging** - Complete event log for every run
5. **Backup & Export** - PostgreSQL dump, JSON/CSV export for analysis

---

## 🤖 Multi-Agent Control Architecture

### Unified Agent Types

| Agent | Detection Method | Control Method | Session ID Source |
|--------|-----------------|---------------|------------------|
| **Ralph** | Reads `.ralph/logs/ralph-summary-*.md` | tmux send-keys | Session from spec names |
| **Claude Code** | Active `claude` process | CLI wrapper + stdin | Session from `claude` output |
| **Cursor** | Active `cursor` process | CLI wrapper + stdin | Session from `cursor` output |
| **Terminal** | tmux sessions | tmux send-keys | User-provided name |
| **IDEs** | Future | VS Code API | TBD | Future |

### Unified Session Model

```typescript
interface AgentSession {
  id: string;              // UUID
  type: AgentType;         // 'ralph' | 'claude' | 'cursor' | 'terminal'
  name: string;             // User-provided or auto-generated
  state: 'idle' | 'running' | 'waiting' | 'error';
  startTime: Date;
  lastHeartbeat: Date;
  metadata: {
    // Ralph: { currentSpec, totalSpecs, specsCompleted }
    // Claude: { model, conversationId, messageCount }
    // Cursor: { agentType, taskDescription, progress }
    // Terminal: { sessionName, command, pid }
  };
}
```

### Dashboard UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Agent Monitor                                                 │
├─────────────────────────────────────────────────────────────┤
│  Filter: [All] [Ralph] [Claude] [Cursor] [Terminal]     │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Ralph Sessions                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ nonprofit-matcher                                │  │  │
│  │  │ Status: Running (3/11 specs)                   │  │  │
│  │  │ Current: CR-02-typography (67%)               │  │  │
│  │  │ ┌──────────────────────────────────────────────┐│  │ │
│  │  │ │ Controls: [Pause] [Skip] [Stop]          ││  │ │
│  │  │ └──────────────────────────────────────────────┘│  │ │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ Claude Sessions                                       │  │
│  │  │  ┌──────────────────────────────────────────────┐│  │ │
│  │  │  │ claude-abc123 (gemini-1.5-flash)           ││  │ │
│  │  │  │ Status: Idle, waiting for input             ││  │ │
│  │  │  │ ┌──────────────────────────────────────────┐│ │ │ │
│  │  │  │ │ Input: "Explain this error..."         ││ │ │ │
│  │  │  │ │ [Send] [Clear]                          ││ │ │ │
│  │  │  │ └──────────────────────────────────────────┘│ │ │ │
│  │  │ └──────────────────────────────────────────────┘│  │ │
│  │  │                                                           │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ Terminal Sessions                                    │  │ │
│  │  │  ┌──────────────────────────────────────────────┐│  │ │
│  │  │  │ ralph-main (1 window)                               ││  │ │
│  │  │  │ Status: Running build                            ││  │ │
│  │  │  │ ┌──────────────────────────────────────────┐││ │ │ │
│  │  │  │ │ Last log: "Compiling..."                   │││ │ │ │
│  │  │  │ │ Controls: [Send] [Detach]                   │││ │ │ │
│  │  │  │ └──────────────────────────────────────────┘│ │ │ │
│  │  │  └──────────────────────────────────────────────┘│  │ │
│  │  │                                                           │  │
│  │  │  (more sessions...)                                     │  │ │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  Controls:                                                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [Refresh Sessions] ← Re-scan all agents           │  │
│  │ [Start Agent]     ← Start new Ralph/Claude/Cursor    │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Priority

**Phase 1 (Week 2): Ralph + Terminal Only**
- Ralph: Already implemented (tmux control)
- Terminal: Add tmux session detection + basic controls

**Phase 2 (Week 3): Claude Code Integration**
- Claude wrapper script (stdin/stdout)
- Parse Claude responses
- Basic UI: text input + response display

**Phase 3 (Week 4): Cursor Integration**
- Cursor wrapper script
- File selection interface
- Progress tracking

**Phase 4 (Future): IDE Integration**
- VS Code MCP server integration
- File tree explorer control
- Language server protocol

---

## 💬 Query Interface (Yes, You Can Query Ralph & Claude!)

### Unified Query System

**All query commands now route through Control API (port 8002)**

```bash
# Ralph query commands (via tmux)
ralph-query status              # "What is Ralph working on?"
ralph-query error CR-02         # "Why did CR-02 fail?"
ralph-query logs CR-01          # "Show me CR-01 logs"
ralph-query tokens              # "How much has this cost?"
ralph-query eta                 # "How much time left?"
ralph-query skip                # "Skip to next spec"
ralph-query stop                # "Stop Ralph"
ralph-query pause               # "Pause after current spec"
ralph-query resume              # "Resume paused session"

# Claude Code integration (via stdin wrapper)
ralph-query ask "Explain CR-02 failure"
ralph-query ask "What's the token usage trend?"
ralph-query ask "Compare this run to the last one"

# Cursor integration (via stdin wrapper)
ralph-query cursor-status        # "What is Cursor working on?"
ralph-query cursor-pause         # "Pause Cursor agent"

# Terminal integration (via tmux)
ralph-query terminal-list        # "List all terminal sessions"
ralph-query terminal-send <session> <command>  # "Send command to terminal"
```

### How It Works

```
Dashboard → POST /api/8002/query
    ↓
[Query Router] → Detects target agent
    ↓
├─ Ralph queries → tmux send-keys → Parse Ralph output
├─ Claude queries → Claude wrapper → stdin → Parse response
├─ Cursor queries → Cursor wrapper → stdin → Parse response
└─ Terminal queries → tmux send-keys → Return output
    ↓
[Unified Response] → Dashboard displays result
```

### Command Palette Integration (Ctrl+K)

The same commands work via command palette:

```
Press Ctrl+K → Type command → Enter

/status                   → Show Ralph status
/ask "Why did it fail?"   → Ask Claude
/skip CR-02              → Skip specific spec
/tokens                  → Show token usage
```

**All commands route to the SAME backend API**, whether clicked, typed, or invoked via keyboard shortcut.

---

## 📊 Analytics System (Real-Time + On-Demand)

### Dual Analytics Strategy

**Real-Time Metrics (Always Visible)**
- Current session progress
- Token usage in real-time
- Cost projection (current run)
- Success rate (last 24h)
- Pre-aggregated from metric_buckets table

**Historical Analytics (On-Demand Rebuild)**
- Click "Rebuild Analytics" button
- Queries raw events/spec_runs/sessions tables
- Rebuilds materialized views
- Shows long-term trends (last 30 days, 90 days, 1 year)

### Analytics Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Analytics Panel                                             │
├─────────────────────────────────────────────────────────────┤
│  Real-Time Metrics (Live)                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Current Session: 3/11 specs (27%)                     │  │
│  │ Token Usage: 45,231 / ~150,000 (30%)                 │  │
│  │ Cost: $0.14 / ~$0.50 (30%)                           │  │
│  │ ETA: ~45 minutes remaining                            │  │
│  │ Success Rate: 89% (last 24h)                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Historical Analytics (Click to Rebuild)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ [Last 30 Days] [Last 90 Days] [Last Year]            │  │
│  │                                                        │  │
│  │ Total Sessions: 23                                    │  │
│  │ Success Rate: 87%                                     │  │
│  │ Total Cost: $12.45                                    │  │
│  │ Avg Session Duration: 3h 24m                          │  │
│  │                                                        │  │
│  │ Trend: [Graph] Improving (+12% vs last period)       │  │
│  │                                                        │  │
│  │ Top Failed Specs:                                     │  │
│  │  1. CR-02-typography (3 failures)                    │  │
│  │  2. CR-05-api-integration (2 failures)               │  │
│  │                                                        │  │
│  │ Cost Over Time: [Graph]                               │  │
│  │ Session Duration: [Graph]                             │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Controls:                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [Rebuild Analytics] ← Recalculate from raw events   │  │
│  │ [Export to CSV]    ← Download analytics data        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### On-Demand Rebuild Process

```python
async def rebuild_analytics(time_range: str):
    """Rebuild analytics from raw events"""

    # 1. Invalidate old materialized views
    await execute("REFRESH MATERIALIZED VIEW CONCURRENTLY session_summaries")

    # 2. Aggregate spec_runs table
    spec_stats = await execute("""
        SELECT
            DATE_TRUNC('{time_range}', start_time) AS bucket,
            COUNT(*) AS total_specs,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
            AVG(duration_seconds) AS avg_duration,
            SUM(tokens_used) AS total_tokens
        FROM spec_runs
        WHERE start_time > NOW() - INTERVAL '{time_range}'
        GROUP BY bucket
        ORDER BY bucket DESC
    """)

    # 3. Calculate cost trends
    cost_trends = await execute("""
        SELECT
            DATE_TRUNC('{time_range}', start_time) AS bucket,
            SUM(cost_usd) AS total_cost
        FROM spec_runs
        WHERE start_time > NOW() - INTERVAL '{time_range}'
        GROUP BY bucket
        ORDER BY bucket DESC
    """)

    # 4. Identify top failures
    top_failures = await execute("""
        SELECT
            spec_id,
            COUNT(*) AS failure_count
        FROM spec_runs
        WHERE status = 'failed'
          AND start_time > NOW() - INTERVAL '{time_range}'
        GROUP BY spec_id
        ORDER BY failure_count DESC
        LIMIT 10
    """)

    return {
        "spec_stats": spec_stats,
        "cost_trends": cost_trends,
        "top_failures": top_failures
    }
```

### Database Schema for Analytics

```sql
-- Pre-aggregated buckets (fast dashboard queries)
CREATE TABLE metric_buckets (
  id BIGSERIAL PRIMARY KEY,
  bucket_time TIMESTAMPTZ NOT NULL,  -- 5-minute buckets
  event_type VARCHAR(100),
  count INTEGER NOT NULL,
  avg_duration_seconds NUMERIC,
  INDEX idx_metrics_time (bucket_time DESC)
);

-- Materialized view for session summaries
CREATE MATERIALIZED VIEW session_summaries AS
SELECT
  DATE_TRUNC('day', start_time) AS day,
  COUNT(*) AS total_sessions,
  SUM(specs_completed) AS total_specs,
  AVG(CAST(cost_usd AS NUMERIC)) AS avg_cost,
  SUM(CASE WHEN execution_state = 'completed' THEN 1 ELSE 0 END) AS completed_sessions
FROM sessions
GROUP BY day
ORDER BY day DESC;

-- Refresh on-demand (not auto-refreshed)
REFRESH MATERIALIZED VIEW CONCURRENTLY session_summaries;
```

### Benefits

**Real-Time Metrics:**
- Always visible, no rebuild needed
- Fast queries (from pre-aggregated buckets)
- Shows current session progress

**Historical Analytics:**
- On-demand rebuild (click button)
- Queries raw data (accurate)
- Shows long-term trends
- Identifies patterns and issues

**Flexibility:**
- Choose time range (30 days, 90 days, 1 year)
- Export to CSV for external analysis
- Rebuild only when needed (save resources)

---

## 🔔 Enhanced Notification System

### Dual Notification Types

**1. Audio Notifications (Toggleable)**
- Sound alerts on spec completion/failure
- Different sounds for different events
- Volume control
- Can be disabled

**2. Deployment Alerts (Toggleable)**
- Desktop notifications when Ralph completes
- Browser notification permission required
- Shows summary message
- Click to open dashboard

### Notification Settings UI

```
┌─────────────────────────────────────────────────────────────┐
│  Notification Settings                                       │
├─────────────────────────────────────────────────────────────┤
│  Audio Notifications                                         │
│  ☑ Enable audio alerts                                       │
│  Volume: [────●────] 70%                                     │
│  Sounds:                                                     │
│    ☑ Spec completed → [chime.wav]                    │  │
│    ☑ Spec failed → [error.wav]                      │  │
│    ☑ Session completed → [success.wav]                │  │
│    ☑ Session failed → [critical.wav]                 │  │
│                                                              │
│  Deployment Alerts                                           │
│  ☑ Enable desktop notifications                              │
│  ☑ Notify on session complete                                │
│  ☑ Notify on session failed                                  │
│  ☑ Notify on critical errors                                 │
│                                                              │
│           [Save]  [Cancel]                                   │
└─────────────────────────────────────────────────────────────┘
```

### Audio Implementation (Web Audio API)

```typescript
class AudioManager {
  private context: AudioContext;
  private sounds: Map<string, AudioBuffer>;

  async play(alertType: 'spec_complete' | 'spec_failed' | 'session_complete') {
    const buffer = this.sounds.get(alertType);
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);
    source.start();
  }

  async loadSounds() {
    // Load sound files from public/sounds/
    this.sounds.set('spec_complete', await loadSound('/sounds/chime.wav'));
    this.sounds.set('spec_failed', await loadSound('/sounds/error.wav'));
    this.sounds.set('session_complete', await loadSound('/sounds/success.wav'));
  }
}
```

### Desktop Notifications (Browser API)

```typescript
class NotificationManager {
  async requestPermission() {
    if (Notification.permission === 'default') {
      await Notification.requestPermission();
    }
  }

  show(title: string, body: string, onClick: () => void) {
    if (Notification.permission === 'granted') {
      const notification = new Notification(title, {
        body: body,
        icon: '/favicon.ico',
        tag: 'ralph-monitoring'
      });

      notification.onclick = () => {
        window.focus();
        onClick();
        notification.close();
      };

      // Auto-close after 5 seconds
      setTimeout(() => notification.close(), 5000);
    }
  }
}

// Usage
notificationManager.show(
  'Ralph Session Complete',
  'nonprofit-matcher: 11/11 specs completed in 3h 24m. Cost: $0.47',
  () => window.location.href = '/dashboard'
);
```

### Notification Events

```python
# Backend: Send notification event via WebSocket
await broadcast_to_websocket({
    "type": "notification",
    "data": {
        "event_type": "session_complete",
        "session_id": session_id,
        "title": "Ralph Session Complete",
        "body": f"{project_name}: {specs_completed}/{total_specs} specs completed in {duration}. Cost: ${cost}",
        "sound": "success.wav"
    }
})
```

### User Configurable

**Audio Settings:**
- Enable/disable all audio
- Adjust volume (0-100%)
- Customize sound files (upload custom)
- Per-event toggles

**Deployment Alerts:**
- Enable/disable desktop notifications
- Choose which events trigger notifications
- Set quiet hours (don't notify between 10pm-6am)
- Browser permission management

---

## 🎨 Dashboard Features (Enhanced)

### MVP (Week 1)

```
┌─────────────────────────────────────────────────────────────┐
│ Ralph Monitor - nonprofit-matcher              [Running] ●   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Connection: [🟢 Live WebSocket] [Toggle Mode]               │
│                                                              │
│ Progress: ████████░░░░░░░░░░░░░ 3/11 specs (27%)             │
│ ETA: ~45 minutes remaining                                    │
│                                                              │
│ Current Spec:                                                │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ CR-02-typography-consolidation                           │  │
│ │ Status: ⏳ In Progress (Attempt 2/3)                   │  │
│ │ Phase: Running E2E tests...                             │  │
│ │ Started: 23:12 UTC | Duration: 3m 14s                  │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Spec Timeline:                                               │
│ [✓ CR-01] [→ CR-02] [  CR-03] [  CR-04] [  CR-05]         │
│                                                              │
│ Live Logs:                                                   │
│ [23:14:42] Running E2E tests...                              │
│ [23:14:49] ❌ E2E tests failed                                │
│ [23:15:46] CR created: CR-fix-CR-02...                       │
│                                                              │
│ Controls:                                                    │
│ [⏸ Pause] [▶ Resume] [⏭ Skip] [⏹ Stop]                    │
│                                                              │
│ OR Type Custom Instruction:                                   │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ Type custom instruction for Ralph...                 │  │
│ │ Auto-send in: 15s (typing resets timer) [Send]     │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                              │
│ Commands (Ctrl+K): /status /pause /skip /ask "question"     │
└─────────────────────────────────────────────────────────────┘
```

### Enhanced (Week 2-3)

- **Bidirectional Control:** Pause, resume, skip, stop from dashboard
- **Command Palette:** Press Ctrl+K for slash commands
- **Dual-Mode Intervention:** Buttons OR custom feedback with timeout
- **Error Notifications:** Alert popups on test failures
- **Session History:** Browse past autonomous runs (from database)
- **Cost Analytics:** Real-time token usage, cost projection
- **Multi-Agent Monitor:** Control Ralph, Claude, Cursor, Terminal
- **Connection Mode Toggle:** WebSocket (real-time) OR polling (on-demand)

### Production (Week 4)

- **Claude Code Integration:** Ask questions about failures via stdin wrapper
- **Audio Alerts:** Toggleable sound notifications on spec completion
- **Deployment Alerts:** Toggleable desktop notifications
- **Enhanced Analytics:** Real-time metrics + on-demand history rebuild
- **Automated Reports:** PDF/Markdown summaries emailed to you
- **Environment Detection:** Auto-configures for VM vs local
- **Extended Retention:** 30 days events, 1 year sessions (database-first)

---

## 📅 Implementation Timeline (Updated with User Enhancements)

### Week 1: MVP (Real-Time Monitoring + Database-First)

**Days 1-2: Infrastructure Setup**
```bash
# On VM
cd ~/projects/nonprofit-matcher
mkdir -p monitoring/{api,managers,integrations}
mkdir -p dashboard

# Setup PostgreSQL database
sudo -u postgres createdb ralph_monitoring
psql ralph_monitoring < schema.sql
```

**Days 3-5: Session Manager + Database-First Storage**
- `SessionManager` class (progress tracking)
- `EventStore` class (PostgreSQL IMMEDIATE writes)
- `WebSocketManager` class (event broadcasting AFTER DB write)
- Ralph output reader (parse JSON summaries)
- Database schema: events, sessions, spec_runs tables

**Days 6-7: Basic Dashboard + Dual-Mode Communication**
- Next.js setup with TypeScript
- WebSocket client (auto-reconnect)
- Polling client (fallback)
- Connection mode toggle UI
- Progress bar, current spec, status display

**Deliverable:** Dashboard shows real-time spec progress, all events stored to database ✅

### Week 2: Control (Intervention + Command Interface)

**Days 8-10: Bidirectional WebSocket + Dual-Mode Intervention**
- Dashboard → Ralph commands via Control API
- Pause/resume/abort handlers
- Skip to spec functionality
- UI controls (buttons) + Custom feedback textarea
- Smart timeout (30s default, resets on typing)

**Days 11-12: Command Palette (Slash Commands)**
- Command registry (pause, resume, skip, retry, ask, etc.)
- Command palette UI (Ctrl+K)
- Command parser and router
- Auto-complete and command history

**Days 13-14: Error Notifications + Query API**
- Alert system for test failures
- Error dashboard with stack traces
- FastAPI query endpoints (`/api/query/*`)
- Ralph state file reader

**Deliverable:** Full control from dashboard, slash commands, dual-mode intervention ✅

### Week 3: Enhanced (Multi-Agent + Analytics)

**Days 15-17: Multi-Agent Control Architecture**
- Unified session model (Ralph + Claude + Cursor + Terminal)
- Agent detection (tmux sessions, process scanning)
- Control API routing (per agent type)
- Multi-agent dashboard UI

**Days 18-19: Claude Code + Cursor Integration**
- Claude wrapper script (stdin/stdout)
- Cursor wrapper script (stdin/stdout)
- Query routing (Ralph vs Claude vs Cursor)
- Response parsing and display

**Days 20-21: Analytics System**
- Real-time metrics (from metric_buckets)
- On-demand analytics rebuild
- Historical trends (30 days, 90 days, 1 year)
- Cost/trend aggregation
- Materialized views for performance

**Deliverable:** Multi-agent control, Claude/Cursor integration, analytics ✅

### Week 4: Polish (Notifications + Production)

**Days 22-23: Enhanced Notification System**
- Audio notifications (Web Audio API)
- Desktop notifications (Browser API)
- Notification settings UI (toggleable)
- Sound file management

**Days 24-25: Environment Detection + Extended Retention**
- `EnvironmentDetector` class
- Auto VM vs local configuration
- SSH tunnel instructions
- Database retention policies (30 days events, 1 year sessions)
- Backup/export functionality

**Days 26-28: Automated Reporting**
- PDF/Markdown report generator
- Email/Slack notifications
- Session summaries
- Set-and-forget configuration

**Deliverable:** Production-ready, set-and-forget system with all enhancements ✅

---

## 📁 File Structure

```
ralph-inferno/
├── monitoring/                      # Python backend (NEW)
│   ├── __init__.py
│   ├── config.py                    # Configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app
│   │   ├── websocket.py             # WebSocket handler
│   │   └── query.py                 # Query endpoints
│   ├── managers/
│   │   ├── __init__.py
│   │   ├── session.py               # SessionManager
│   │   ├── timeout.py               # TimeoutManager
│   │   └── state.py                 # StateManager
│   └── integrations/
│       ├── __init__.py
│       ├── ralph_reader.py          # Read Ralph JSON files
│       └── claude_wrapper.py        # Claude Code CLI wrapper
│
├── dashboard/                       # Next.js frontend (NEW)
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx             # Main dashboard
│   │   ├── components/
│   │   │   ├── SessionProgress.tsx
│   │   │   ├── SpecTimeline.tsx
│   │   │   ├── LiveLogs.tsx
│   │   │   ├── QueryPanel.tsx       # ralph-query interface
│   │   │   ├── ClaudeAsk.tsx        # Claude integration
│   │   │   └── Controls.tsx         # Pause/resume/skip
│   │   └── lib/
│   │       ├── websocket.ts         # WebSocket client
│   │       └── api.ts               # REST client
│   └── public/
│       └── sounds/                  # Audio alert files
│
└── .ralph/
    └── sessions/                    # Session history storage
```

---

## 🎁 Bonus Features

### 1. Multi-Ralph Orchestration
Monitor multiple projects simultaneously

### 2. Spec Dependency Visualization
Show dependency tree with progress

### 3. Automated Reporting
PDF/Markdown summaries after each session

### 4. Intervention Recommendations
AI suggests actions when specs fail repeatedly

---

## 🎯 Success Criteria

| Week | Criteria | How to Verify |
|------|----------|---------------|
| 1 | Dashboard shows real-time progress | Start Ralph, see updates in browser |
| 2 | Can pause/resume from dashboard | Click pause, verify Ralph stops |
| 3 | Can ask Claude about failures | Query "Explain CR-02", get answer |
| 4 | Generates automated reports | Run completes, PDF appears |

---

## 🚀 Quick Start (After Implementation)

```bash
# On VM: Start monitoring infrastructure
cd ~/projects/nonprofit-matcher/monitoring
python -m api.main &                    # WebSocket on 8001
python -m api.query.main &               # API on 8002

# On VM: Start dashboard
cd ~/projects/nonprofit-matcher/dashboard
npm run dev &                            # Dashboard on 8003

# From Windows: Open browser
http://192.168.206.128:8003

# Start Ralph (as usual)
cd ~/projects/nonprofit-matcher
bash .ralph/scripts/ralph.sh --orchestrate

# Dashboard auto-detects Ralph and starts monitoring!
```

---

## 📚 Related Documentation

This plan was synthesized from:

### Original Planning (2026-01-23)
- **Agent Reasoning:** `.taskmaster/docs/plans/atoms/` - Individual AOT atoms with context
- **Sequential Thinking:** `.taskmaster/docs/plans/SYNTHESIS-THINKING.md` - Complete thought chain
- **MCP Feedback Research:** `.taskmaster/docs/research/mcp-feedback-enhanced-analysis.md`
- **Query Interface Spec:** `.taskmaster/docs/research/ralph-query-interface-spec.md`
- **Integration Plan:** `.taskmaster/docs/research/ralph-monitoring-integration-plan.md`
- **Monitoring Research:** `.taskmaster/docs/research/ralph-monitoring-system-research.md`

### User Enhancement Planning (2026-01-23 Update)
- **Command Interface:** `COMMAND-INTERFACE.md` - Slash commands + UI controls design
- **Polling Hybrid:** `POLLING-HYBRID.md` - WebSocket + polling toggle design
- **Database First:** `DATABASE-FIRST.md` - PostgreSQL as source of truth architecture
- **Multi-Agent Control:** `MULTI-AGENT-CONTROL.md` - Unified interface for all agents
- **Dual-Mode Intervention:** Agent a029eb5 output - Quick actions + custom feedback with timeout
- **Analytics System:** Agent a20bb64 output - Real-time metrics + on-demand history rebuild
- **Prompt Management:** Agent a5e5494 output - Analysis of MCP prompt management (NOT used for specs)

### MCP Feedback Enhanced Research
- **MCP Key Learnings:** `MCP-KEY-LEARNINGS.md` - Core architectural concepts extracted
- **Repository:** https://github.com/Minidoracat/mcp-feedback-enhanced

---

## 📊 AOT Decomposition Summary

### Original Session (2026-01-23)
**Method:** Atom of Thoughts (AoT)
**Total Atoms:** 5

1. **Research mcp-feedback-enhanced** (Complex → deep-researcher agent)
2. **Design port architecture** (Simple → direct)
3. **Define query interface** (Medium → deep-researcher agent)
4. **Design control/feedback integration** (Complex → general-purpose agent)
5. **Create Super Duper Plan synthesis** (Complex → mcp_st_sequentialthinking)

**Sub-agents Deployed:** 3 (deep-researcher ×2, general-purpose ×1)
**Parallel Execution:** Yes (atoms 1, 3, 4 ran simultaneously)
**Sequential Thinking:** 8 thoughts for final synthesis

### User Enhancement Session (2026-01-23)
**Method:** Atom of Thoughts (AoT)
**Total Atoms:** 9

1. **Research MCP prompt management concept** (Complex → deep-researcher agent a5e5494)
2. **Design command execution interface** (Simple → direct)
3. **Design user feedback vs intervention system** (Complex → general-purpose agent a029eb5)
4. **Update architecture for multi-session control** (Medium → direct, after architect agent failed)
5. **Design polling + WebSocket hybrid** (Simple → direct)
6. **Update data persistence strategy** (Simple → direct)
7. **Update notification system** (Simple → direct)
8. **Design analytics system** (Complex → general-purpose agent a20bb64)
9. **Update master plan with all enhancements** (Complex → THIS DOCUMENT)

**Sub-agents Deployed:** 3 (deep-researcher ×1, general-purpose ×2)
**Parallel Execution:** Yes (multiple agents ran simultaneously)
**Documents Created:** 7 design documents + 3 agent outputs

---

## ✅ Success Criteria (Updated with User Enhancements)

| Week | Criteria | How to Verify |
|------|----------|---------------|
| 1 | Dashboard shows real-time progress, database-first | Start Ralph, see updates in browser, check PostgreSQL for events |
| 2 | Full control + dual-mode intervention + slash commands | Click pause (works), type custom feedback with timeout (works), Ctrl+K opens command palette |
| 3 | Multi-agent control + analytics | Control Ralph + Claude + Cursor from dashboard, rebuild analytics shows historical trends |
| 4 | Production-ready with notifications + extended retention | Audio/deployment alerts work, database has 30 days events / 1 year sessions |

### Key User Requirements Met

✅ **Command execution from UI** - UI controls (primary) + slash commands (secondary via Ctrl+K)
✅ **Dual-mode intervention** - Quick actions (buttons) + custom feedback (textarea with timeout)
✅ **Spec priority management** - Dedicated system (NOT MCP prompt management)
✅ **Audio + deployment notifications** - Both toggleable in settings
✅ **Analytics** - Real-time metrics + on-demand history rebuild (full history button)
✅ **Environment detection** - Auto-detects VM vs local for all agents
✅ **Extended retention** - 30 days events, 1 year sessions (SQL is cheap!)
✅ **Polling + WebSocket hybrid** - User toggle between real-time and on-demand
✅ **Database-first** - PostgreSQL as source of truth (especially for overnight monitoring)
✅ **Multi-agent control** - Ralph + Claude + Cursor + Terminal from unified dashboard

---

**Status:** ✅ COMPLETE - All user enhancements integrated, ready for implementation

**Last Updated:** 2026-01-23 (User enhancements added)
**Version:** 2.0 (Enhanced with user feedback)
