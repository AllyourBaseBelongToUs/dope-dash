# Command Execution Interface Design

**Decision:** Slash Commands (Skills Injection)

---

## User's Question

> "Command execution from UI, actually useful! is it slash commands or which? slash commands or skills injection form us would be dope"

---

## Analysis

### Option 1: Slash Commands
**What:** Commands like `/pause`, `/skip`, `/retry`, `/status`
**Pros:**
- Familiar from Discord, Slack, CLI tools
- Quick to type, discoverable
- Can have tab completion

**Cons:**
- Need to parse command syntax
- Limited to what we define
- Requires command registry

### Option 2: Skills Injection
**What:** "Inject" skills into running Ralph/Claude sessions via MCP
**Pros:**
- Leverages existing skill system
- Can modify agent behavior mid-session
- Very flexible

**Cons:**
- More complex to implement
- Requires understanding MCP skill format
- Overkill for simple commands

### Option 3: Dedicated UI Controls
**What:** Buttons, forms, text areas in dashboard
**Pros:**
- Most intuitive for non-technical users
- Can show labels, tooltips, examples
- Easier to discover (see the button, know what it does)

**Cons:**
- Takes more screen space
- Can feel cluttered if too many options

---

## Recommendation: Hybrid Approach

**Primary: UI Controls (Buttons + Text Area)**
- Most intuitive for monitoring dashboard
- Buttons for quick actions (Pause, Skip, Retry)
- Text area for custom instructions
- This is the main interface

**Secondary: Slash Commands (Power User Feature)**
- For users who prefer keyboard over mouse
- Command palette modal (Ctrl+K or Cmd+K style)
- Auto-complete for commands
- Maps to same backend actions as UI controls

**Why This Order:**
1. Build UI controls first (Week 1-2) - gets you working quickly
2. Add slash commands later (Week 3-4) - power user feature
3. Slash commands call the SAME backend API as UI controls

---

## Slash Command Syntax

```
/:<command> [arguments]

Commands:
/pause                   - Pause at next safe point
/resume                  - Continue from pause
/skip                    - Skip current spec
/retry [spec-id]          - Retry a specific spec
/stop                    - Abort entire build
/status                  - Show current status
/ask <question>          - Ask Claude something
/logs [spec-id]           - Show logs for spec
/tokens                  - Show token usage
/eta                     - Show estimated time remaining
/settings                - Open settings modal
/help                    - Show all commands
```

---

## Implementation Architecture

### Backend API (Unified)

```
┌─────────────────────────────────────────────────────────────┐
│                    Ralph Control API                        │
├─────────────────────────────────────────────────────────────┤
│  POST /api/intervention                                       │
│  POST /api/query                                              │
│  POST /api/ask (Claude Code integration)                     │
└──────────────┬────────────────────────────┬───────────────────┘
               │                            │
               ▼                            ▼
         UI Controls              Slash Command Parser
         (buttons/text)            (maps to same API)
```

### Command Palette UI

```
┌─────────────────────────────────────────────────────────────┐
│  >                                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Commands                                    Type to search │  │
│  │ ────────────────────────────────────────────────── │  │
│  │ /pause                                     Quick action    │  │
│  │ /resume                                    Quick action    │  │
│  │ /skip                                      Quick action    │  │
│  │ /retry                                     Quick action    │  │  │
│  │ /stop                                      Quick action    │  │  │
│  │ /status                                    Information     │  │
│  │ /logs                                      Information     │  │  │
│  │ /ask <question>                            Claude Code     │  │
│  │ /settings                                  Navigation      │  │
│  │ ────────────────────────────────────────────────── │  │
│  │                                                           │  │
│  │              [↓] select  [Enter] execute               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  Recent:                                                    │
│  /ask "Why did CR-02 fail?"                              │
│  /skip                                                      │
│  /status                                                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Bindings

| Key | Action | Platform |
|-----|--------|----------|
| `Ctrl+K` / `Cmd+K` | Open command palette | All |
| `Escape` | Close command palette | All |
| `↑` / `↓` | Navigate history | All |
| `Enter` | Execute selected command | All |

---

## Command Registry

```typescript
// commands/registry.ts
export const commandRegistry: Command[] = [
  {
    id: 'pause',
    name: 'Pause',
    description: 'Pause execution at next safe point',
    category: 'control',
    action: 'pause',
    icon: '⏸',
    shortcut: 'Cmd+Shift+P'
  },
  {
    id: 'resume',
    name: 'Resume',
    description: 'Continue from pause',
    category: 'control',
    action: 'resume',
    icon: '▶️',
    shortcut: 'Cmd+Shift+R'
  },
  {
    id: 'skip',
    name: 'Skip',
    description: 'Skip current spec',
    category: 'control',
    action: 'skip',
    icon: '⏭',
    shortcut: 'Cmd+Shift+S'
  },
  {
    id: 'retry',
    name: 'Retry',
    description: 'Retry current or specified spec',
    category: 'control',
    action: 'retry',
    icon: '🔄',
    args: [{ name: 'specId', optional: true }]
  },
  {
    id: 'ask',
    name: 'Ask Claude',
    description: 'Ask Claude Code a question',
    category: 'claude',
    action: 'ask',
    args: [{ name: 'question', required: true }],
    icon: '🤖'
  },
  {
    id: 'status',
    name: 'Status',
    description: 'Show current status and progress',
    category: 'information',
    action: 'status',
    icon: '📊'
  },
  {
    id: 'logs',
    name: 'Logs',
    description: 'Show logs for a spec',
    category: 'information',
    action: 'logs',
    args: [{ name: 'specId', optional: true }],
    icon: '📜'
  }
]
```

---

## Examples

### Example 1: Quick Skip via Button
```
User: Clicks [Skip] button in dashboard
System: POST /api/intervention { action: 'skip' }
Ralph: "Skipping CR-02, starting CR-03"
Dashboard: Status updates to "CR-03 running"
```

### Example 2: Same Action via Command
```
User: Presses Ctrl+K, types "/s", presses Enter
System: POST /api/intervention { action: 'skip' }
Result: Same as button click
```

### Example 3: Ask Claude via Command
```
User: Presses Ctrl+K, types "/ask Why did CR-02 fail?"
System: POST /api/ask { question: "Why did CR-02 fail?" }
Claude: Analyzes logs, returns explanation
Dashboard: Displays Claude's response in modal
```

### Example 4: Quick Status Check
```
User: Presses Ctrl+K, types "/status", Enter
System: POST /api/query { query: 'status' }
Dashboard: Shows modal with current status:
  "CR-03 running, 3 of 11 specs complete (27%),
   ETA: ~45 minutes"
```

---

## Implementation Phases

### Phase 1 (Week 2): UI Controls Only
- Buttons in dashboard
- Text area for custom instructions
- Backend API endpoints
- NO slash commands yet

### Phase 2 (Week 3): Command Palette
- Command palette modal
- Command registry
- Command parser
- Auto-complete
- Maps to existing API endpoints

### Phase 3 (Week 4): Enhanced Features
- Command shortcuts
- Command history
- Favorite commands
- Custom user commands

---

## Final Answer to User's Question

**"Is it slash commands or skills injection?"**

**Answer: UI Controls + Slash Commands (no skills injection needed)**

- **Primary:** Buttons and text area (intuitive, always visible)
- **Secondary:** Slash commands via command palette (power user feature)
- **Both map to same backend API** - no duplication needed

**Why not skills injection?**
- Overkill for simple pause/skip commands
- Skills system is complex (skills format, injection, lifecycle)
- Slash commands give same benefit with less complexity
- UI controls are more discoverable than injected skills

**For "contextual" commands:**
- User types freeform instructions in text area
- That IS the "custom instruction" mode (no skills injection needed)
- Ralph/Claude interpret natural language via LLM

**Bonus:** Command palette can show contextual suggestions based on current state (e.g., only show /retry when a spec just failed).

---

## Success Criteria

✅ Slash commands route to same API as UI controls
✅ Command palette discoverable via Ctrl+K
✅ Commands have auto-complete and descriptions
✅ No skills injection overhead
✅ UI controls remain primary interface
