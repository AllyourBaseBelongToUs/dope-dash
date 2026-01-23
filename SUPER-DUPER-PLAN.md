# 🚀 SUPER DUPER PLAN - Ralph Inferno Monitoring Dashboard

**Date Created:** 2026-01-23
**Status:** Ready for Implementation
**Timeline:** 4 weeks (MVP in Week 1)
**AOT Session:** 2025-01-23 decomposition

---

## 📊 Executive Summary

**Vision:** A unified web dashboard that monitors multiple autonomous Ralph sessions on your VM, accessible from Windows with real-time updates, intervention capabilities, Claude Code integration, and zero port conflicts.

**Timeline:** 4 weeks (MVP in Week 1, production-ready by Week 4)

**Architecture:** VM-based Python backend + Next.js frontend + PostgreSQL persistence

---

## 🎯 What You're Getting

| Week | Capability | Example |
|------|------------|---------|
| **1** | **Real-time monitoring** | "3 of 11 specs complete, currently running: CR-02" |
| **2** | **Control & intervention** | Pause, skip, or stop specs from browser |
| **3** | **Claude Code integration** | Ask "Why did CR-02 fail?" → get explanation |
| **4** | **Production automation** | PDF reports, audio alerts, set-and-forget |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Windows Machine                        │
├─────────────────────────────────────────────────────────────────┤
│  Browser: http://192.168.206.128:8003/dashboard               │
│  ├─ Real-time progress (WebSocket pushes)                     │
│  ├─ Control buttons (pause/resume/skip)                        │
│  ├─ Query panel ("ralph-query status")                         │
│  └─ Claude Code integration ("Explain CR-02 failure")          │
└─────────────────────────────────────────────────────────────────┘
                    ↕ HTTPS/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                       VM (192.168.206.128)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Dev Servers (localhost:3000-3099)                              │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ nonprofit-matcher → 127.0.0.1:3000                   │      │
│  │ project-alpha     → 127.0.0.1:3001                   │      │
│  │ project-beta      → 127.0.0.1:3002                   │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                   │
│  Ralph Sessions (tmux)                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ tmux session "ralph-nonprofit"                        │      │
│  │ tmux session "ralph-alpha"                            │      │
│  │ tmux session "ralph-beta"                             │      │
│  └──────────────────────────────────────────────────────┘      │
│                         │                                      │
│                         │ Ralph Output Capture               │
│                         ▼                                      │
│  Monitoring Infrastructure (0.0.0.0:8001-8003)                    │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Port 8001: WebSocket Server (FastAPI)                │      │
│  │   - Receives Ralph events                             │      │
│  │   - Broadcasts to dashboard                           │      │
│  │   - Accepts intervention commands                     │      │
│  ├──────────────────────────────────────────────────────┤      │
│  │ Port 8002: Query API (FastAPI)                        │      │
│  │   - ralph-query commands                              │      │
│  │   - Claude Code subprocess wrapper                    │      │
│  │   - Token/cost analytics                              │      │
│  ├──────────────────────────────────────────────────────┤      │
│  │ Port 8003: Dashboard (Next.js)                        │      │
│  │   - React UI with real-time updates                   │      │
│  │   - Auto-refreshes on WebSocket events                │      │
│  └──────────────────────────────────────────────────────┘      │
│                         │                                      │
│                         ▼                                      │
│  PostgreSQL (localhost:5432)                                   │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ ralph_monitoring database                              │      │
│  │   - Session history (72-hour retention)               │      │
│  │   - Log entries (BRIN indexed)                        │      │
│  │   - Analytics (cost, duration, success rate)          │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Port Architecture (Zero Conflicts)

| Port Range | Purpose | Binding | Access From |
|------------|---------|---------|-------------|
| **3000-3099** | Dev servers | `127.0.0.1` (localhost) | SSH tunnel only |
| **8001** | WebSocket | `0.0.0.0` (all interfaces) | Windows: `192.168.206.128:8001` |
| **8002** | Query API | `0.0.0.0` (all interfaces) | Windows: `192.168.206.128:8002` |
| **8003** | Dashboard | `0.0.0.0` (all interfaces) | Windows: `http://192.168.206.128:8003` |
| **5432** | PostgreSQL | `127.0.0.1` (localhost) | Local only |

**Why This Works:**
- Dev servers bind to localhost → can't conflict with monitoring ports
- Monitoring binds to explicit IP `0.0.0.0` → accessible from Windows
- Different ranges (3000s vs 8000s) → impossible to confuse

---

## 💬 Query Interface (Yes, You Can Query Ralph & Claude!)

### Ralph Query Commands

```bash
# Simple commands
ralph-query status              # "What is Ralph working on?"
ralph-query error CR-02         # "Why did CR-02 fail?"
ralph-query logs CR-01          # "Show me CR-01 logs"
ralph-query tokens              # "How much has this cost?"
ralph-query eta                 # "How much time left?"

# Control commands
ralph-query skip                # "Skip to next spec"
ralph-query stop                # "Stop Ralph"
ralph-query pause               # "Pause after current spec"
ralph-query resume              # "Resume paused session"
```

### Claude Code Integration

```bash
# Dashboard wraps Claude Code CLI
ralph-query ask "Explain CR-02 failure"
ralph-query ask "What's the token usage trend?"
ralph-query ask "Compare this run to the last one"

# How it works:
# 1. Dashboard sends query to API (port 8002)
# 2. API spawns: claude "explain CR-02 failure"
# 3. Captures Claude output
# 4. Returns formatted response to dashboard
```

---

## 🎨 Dashboard Features

### MVP (Week 1)

```
┌─────────────────────────────────────────────────────────────┐
│ Ralph Monitor - nonprofit-matcher              [Running] ●   │
├─────────────────────────────────────────────────────────────┤
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
│ [⏸ Pause] [⏭ Skip] [⏹ Stop]                                │
└─────────────────────────────────────────────────────────────┘
```

### Enhanced (Week 2-3)

- **Bidirectional Control:** Pause, resume, skip, stop from dashboard
- **Error Notifications:** Alert popups on test failures
- **Session History:** Browse past autonomous runs
- **Cost Analytics:** Real-time token usage, cost projection
- **Multi-Ralph:** Monitor multiple projects simultaneously

### Production (Week 4)

- **Claude Code Integration:** Ask questions about failures
- **Audio Alerts:** Sound notifications on spec completion
- **Automated Reports:** PDF/Markdown summaries emailed to you
- **Environment Detection:** Auto-configures for VM vs local

---

## 📅 Implementation Timeline

### Week 1: MVP (Real-Time Monitoring)

**Days 1-2: Infrastructure Setup**
```bash
# On VM
cd ~/projects/nonprofit-matcher
mkdir -p monitoring/{api,managers,integrations}
mkdir -p dashboard
```

**Days 3-5: Session Manager + WebSocket**
- `SessionManager` class (progress tracking)
- `WebSocketManager` class (event broadcasting)
- Ralph output reader (parse JSON summaries)

**Days 6-7: Basic Dashboard**
- Next.js setup with TypeScript
- WebSocket client (auto-reconnect)
- Progress bar, current spec, status display

**Deliverable:** Dashboard shows real-time spec progress ✅

### Week 2: Control (Intervention Capabilities)

**Days 8-10: Bidirectional WebSocket**
- Dashboard → Ralph commands
- Pause/resume/abort handlers
- Skip to spec functionality

**Days 11-12: Query API**
- FastAPI endpoints (`/api/query/*`)
- Ralph state file reader
- Command parser

**Days 13-14: Error Notifications**
- Alert system for test failures
- Error dashboard with stack traces
- Notification preferences

**Deliverable:** Full control from dashboard, can intervene autonomously ✅

### Week 3: Enhanced (Deep Insights)

**Days 15-17: Claude Code Integration**
- Subprocess wrapper
- Query routing (Ralph vs Claude)
- Response parsing and display

**Days 18-19: Session History**
- `StateManager` class (JSON persistence)
- History browser UI
- Export functionality

**Days 20-21: Cost Analytics**
- Token tracking per spec
- Cost projection algorithm
- Historical trends

**Deliverable:** Ask questions, view history, track costs ✅

### Week 4: Polish (Production Automation)

**Days 22-23: Environment Detection**
- `EnvironmentDetector` class
- Auto VM vs local configuration
- SSH tunnel instructions

**Days 24-25: Audio Alerts**
- Web Audio API integration
- Sound generation (beep, melody)
- Alert preferences

**Days 26-28: Automated Reporting**
- PDF/Markdown report generator
- Email/Slack notifications
- Session summaries

**Deliverable:** Production-ready, set-and-forget system ✅

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

- **Agent Reasoning:** `.taskmaster/docs/plans/atoms/` - Individual AOT atoms with context
- **Sequential Thinking:** `.taskmaster/docs/plans/SYNTHESIS-THINKING.md` - Complete thought chain
- **MCP Feedback Research:** `.taskmaster/docs/research/mcp-feedback-enhanced-analysis.md`
- **Query Interface Spec:** `.taskmaster/docs/research/ralph-query-interface-spec.md`
- **Integration Plan:** `.taskmaster/docs/research/ralph-monitoring-integration-plan.md`
- **Monitoring Research:** `.taskmaster/docs/research/ralph-monitoring-system-research.md`

---

## 📊 AOT Decomposition Summary

**Session Date:** 2026-01-23
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

---

**Status:** ✅ COMPLETE - Ready for implementation
