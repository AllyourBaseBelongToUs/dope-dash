# Multi-Agent Control Architecture

**Goal:** Control Claude Code, Cursor, IDEs, and Terminal from unified Ralph dashboard

---

## User's Vision

> "we would like to control other claude sessions and cursor sessions and IDE sessions too, since the MCP can be put into them and we have it all ^^ would say terminal for now is the main one, IDEs is future stuff"

**Translation:** Dashboard becomes unified control center for ALL agent types, not just Ralph.

---

## Agent Types & Control Methods

| Agent | Detection Method | Control Method | Session ID Source |
|--------|-----------------|---------------|------------------|
| **Ralph** | Reads `.ralph/logs/ralph-summary-*.md` | tmux send-keys | Session from spec names |
| **Claude Code** | Active `claude` process | CLI wrapper + stdin | Session from `claude` output |
| **Cursor** | Active `cursor` process | CLI wrapper + stdin | Session from `cursor` output |
| **Terminal** | tmux sessions | tmux send-keys | User-provided name |
| **IDEs** | Future | VS Code API | TBD | Future |

---

## Unified Session Model

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

---

## Detection Strategy

### Ralph (Already Implemented)
```python
def detect_ralph_sessions():
    sessions = []

    # Read Ralph summaries
    for summary_file in glob.glob('.ralph/logs/ralph-summary-*.md'):
        with open(summary_file) as f:
            # Parse "Results: 12/11 specs, 1 completed"
            # Extract current spec index, total specs
            sessions.append(parse_ralph_summary(f))

    return sessions
```

### Claude Code
```python
def detect_claude_sessions():
    sessions = []

    # Check for active claude processes
    result = subprocess.run(['pgrep', '-f', 'claude'], capture_output=True)

    for line in result.stdout.split('\n'):
        pid = extract_pid(line)
        sessions.append({
            'type': 'claude',
            'name': f'claude-{pid[:8]}',  # Short name
            'pid': pid,
            'state': 'running'
        })

    return sessions
```

### Cursor
```python
def detect_cursor_sessions():
    sessions = []

    # Check for active cursor processes
    result = subprocess.run(['pgrep', '-f', 'cursor'], capture_output=True)

    for line in result.stdout.split('\n'):
        pid = extract_pid(line)
        sessions.append({
            'type': 'cursor',
            'name': f'cursor-{pid[:8]}',
            'pid': pid,
            'state': 'running'
        })

    return sessions
```

### Terminal (tmux)
```python
def detect_tmux_sessions():
    sessions = []

    # List tmux sessions
    result = subprocess.run(['tmux', 'list-s'], capture_output=True)

    for line in result.stdout.split('\n'):
        if ':' not in line:
            continue

        # Parse: "session_name: 1 windows (created...)"
        name = line.split(':')[0]
        windows_count = parse_windows_count(line)

        sessions.append({
            'type': 'terminal',
            'name': name,
            'state': 'running',
            'windows_count': windows_count
        })

    return sessions
```

---

## Unified Control Interface

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

---

## Command Routing

### Ralph Commands
```
Dashboard → POST /api/ralph/control
  → Ralph API (port 8002)
  → tmux send-keys -t ralph <command>
  → Response parsed back to dashboard
```

### Claude Code Commands
```
Dashboard → POST /api/claude/control
  → Claude wrapper script
  → stdin: user instruction
  → Parse response from stdout
  → Return to dashboard
```

### Cursor Commands
```
Dashboard → POST /api/cursor/control
  → Cursor wrapper script
  → stdin: user instruction or file selection
  → Parse response
  → Return to dashboard
```

### Terminal Commands
```
Dashboard → tmux send-keys -t <session> <command>
  → Direct tmux control
  → No parsing needed (terminal output is raw)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard Browser                         │
│  ┌──────────────────────────────────────────────────────────┐│ │
│  │  Unified Agent Monitor UI                               ││ │
│  │  ├─ Ralph Sessions                                    ││ │
│  │  ├─ Claude Sessions                                   ││ │
│  │  ├─ Cursor Sessions                                   ││ │
│  │  └─ Terminal Sessions                                 ││ │
│  └──────────────────────────────────────────────────────────┘│ │
└─────────────────────────────────────────────────────────────┘
                          │
         ┌──────────────┴──────────────┐
         │                           │
         ▼                           ▼
┌──────────────────┐       ┌──────────────────────┐
│  Ralph Control API  │       │  Claude Control API  │
│  (FastAPI)          │       │  (Wrapper Script)     │
│                     │       │                       │
│ port: 8002          │       │ Port: 8004          │
│                     │       │                       │
│ commands:            │       │ commands:            │
│   - pause            │       │   - send prompt       │
│   - resume           │       │   - get response     │
│   - skip             │       │   - new session      │
│                     │       │                       │
└──────────────────┘       └──────────────────────┘
         │                           │
         ▼                           ▼
    tmux send-keys              stdin wrappers
         │                           │
         ▼                           ▼
┌──────────────────┐       ┌──────────────────────┐
│  Ralph (tmux)        │       │  Claude (process)    │
│  Cursor (tmux)        │       │  Terminal (tmux)       │
└──────────────────┘       └──────────────────────┘
```

---

## Session Naming

### Auto-Generated Names
```
Ralph:    nonprofit-matcher, alpha-01, beta-02
Claude:    claude-{session_id}, claude-{timestamp}
Cursor:   cursor-{pid}, cursor-{task-name}
Terminal: ralph-main, debug-server, user-session
```

### User-Provided Names
```
Terminal: User can name tmux sessions: "tmux new-session -s debug"
Ralph:    Session name from project directory
Claude:    Auto-generated, user can override
```

---

## Implementation Priority

### Phase 1 (Week 2): Ralph + Terminal Only
- Ralph: Already implemented (tmux control)
- Terminal: Add tmux session detection + basic controls

### Phase 2 (Week 3): Claude Code Integration
- Claude wrapper script (stdin/stdout)
- Parse Claude responses
- Basic UI: text input + response display

### Phase 3 (Week 4): Cursor Integration
- Cursor wrapper script
- File selection interface
- Progress tracking

### Phase 4 (Future): IDE Integration
- VS Code MCP server integration
- File tree explorer control
- Language server protocol

---

## Key Insights

### Terminal is Main Priority (User Quote)
> "would say terminal for now is the main one"

**Implementation:**
- Primary control interface for tmux sessions
- Send keys to any terminal session
- Display last N lines of output
- Attach/detach buttons

### Environment Detection (Auto-Configure)
```python
class EnvironmentDetector:
    def detect(self) -> str:
        # Check which agent types are active
        # Return 'vm' or 'local'

        # Auto-configure WebSocket URL based on detection
        # VM: ws://0.0.0.0:8001
        # Local: ws://127.0.0.1:8001
```

---

## Success Criteria

✅ Detects all agent types (Ralph, Claude, Cursor, Terminal)
✅ Unified UI for controlling all agents
✅ Session naming (auto + user-provided)
✅ Command routing per agent type
✅ Database stores all session activity
✅ Real-time status updates
