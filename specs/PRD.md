# Ralph Inferno Monitoring Dashboard - Product Requirements Document

**Date:** 2026-01-30
**Project:** Dope-Dash
**Version:** 1.0

---

## Executive Summary

Dope-Dash is a unified web dashboard for monitoring and controlling multiple autonomous AI agents (Ralph Inferno, Claude Code, Cursor, Terminal) running on a VM. The dashboard provides real-time progress monitoring, intervention capabilities, database-first persistence, and comprehensive analytics.

**Reference Architecture:** See SUPER-DUPER-PLAN.md for complete technical design

---

## Design Documents

This PRD consolidates the following detailed design documents located in the project root:

- **SUPER-DUPER-PLAN.md** - Complete 4-week implementation plan (Phases 1-4)
- **COMMAND-INTERFACE.md** - Slash commands, UI controls, intervention system
- **DATABASE-FIRST.md** - PostgreSQL as source of truth architecture
- **MULTI-AGENT-CONTROL.md** - Unified interface for all agent types
- **POLLING-HYBRID.md** - WebSocket/polling dual-mode communication
- **PHASE-5-cleaned.md** - Mission Control portfolio management
- **PHASE-6-RATE-LIMITS.md** - API rate limit & quota management

---

## Must-Have Features (MVP)

### Week 1: Real-Time Monitoring
- PostgreSQL database with events, sessions, spec_runs, metric_buckets tables
- WebSocket server (port 8001) for real-time event broadcasting
- Basic Next.js dashboard (port 8003) showing spec progress
- Dual-mode communication (WebSocket OR polling)
- Real-time progress display: "3 of 11 specs complete, currently running: CR-02"

### Week 2: Control & Intervention
- Bidirectional WebSocket for Dashboard → Ralph commands
- Pause/resume/skip/stop controls via UI buttons
- Command palette (Ctrl+K) with slash commands
- Custom feedback textarea with smart timeout (30s default, resets on typing)
- Error notifications and query API endpoints

### Week 3: Multi-Agent Support
- Unified session model (Ralph + Claude Code + Cursor + Terminal)
- Agent detection (tmux sessions, process scanning)
- Claude wrapper script (stdin/stdout communication)
- Cursor wrapper script (stdin/stdout communication)
- Real-time metrics and on-demand analytics rebuild

### Week 4: Production Polish
- Audio notifications (Web Audio API, toggleable)
- Desktop notifications (Browser API)
- Environment detection (VM vs local)
- Extended retention policies (30 days events, 1 year sessions)
- Automated PDF/Markdown report generation

### Phase 5: Mission Control
- Project portfolio view showing all projects with status
- Per-project controls (pause, resume, skip, stop, retry, restart)
- Command sending system for custom commands
- Bulk operations (multi-select, pause/resue/stop multiple projects)
- Command history with replay functionality
- Agent pool management with load balancing
- Project state machine with full state tracking

### Phase 6: Rate Limit & Quota Management
- Real-time quota tracking per provider (Claude, Gemini, OpenAI, Cursor)
- 429 error detection with exponential backoff retry
- Request queue and throttling when approaching limits
- Auto-pause at 95% quota (lowest priority projects first)
- Multi-channel alerts at 80%/90%/95% thresholds
- /quota CLI command for terminal users

---

## Technical Stack

**Backend:**
- Python with FastAPI (WebSocket server, REST APIs)
- PostgreSQL (localhost:5432, database-first)
- psycopg2 (database connections)
- tmux (terminal control)

**Frontend:**
- Next.js with TypeScript
- Tailwind CSS
- WebSocket client (real-time updates)
- Polling client (on-demand updates)
- Web Audio API (sound alerts)

**Infrastructure:**
- PostgreSQL on VM (source of truth)
- tmux for session management
- Network: Windows ↔ VM (192.168.206.128)

---

## Port Architecture

| Port | Purpose | Binding |
|------|---------|---------|
| 8001 | WebSocket (real-time push) | 0.0.0.0 |
| 8002 | Control API (all agents) | 0.0.0.0 |
| 8003 | Dashboard (Next.js) | 0.0.0.0 |
| 8004 | Analytics API (on-demand) | 0.0.0.0 |
| 5432 | PostgreSQL | 127.0.0.1 |

---

## Success Criteria

- [ ] Dashboard shows real-time spec progress for all agents
- [ ] Can pause/resume/skip any agent from dashboard
- [ ] Slash commands work (Ctrl+K command palette)
- [ ] Multi-agent control unified (Ralph + Claude + Cursor + Terminal)
- [ ] Analytics show historical trends (30/90/365 days)
- [ ] Notifications work (audio + desktop)
- [ ] Mission Control portfolio view manages multiple projects
- [ ] Agent pool management with load balancing
- [ ] Rate limits detected and handled with auto-retry
- [ ] /quota command shows usage statistics

---

## Out of Scope

- IDE integration (VS Code MCP) - Phase 7+
- Hardware tapper device (Stream Deck, MIDI) - Future
- Mobile app - Future
- Multi-user support - Future

---

*End of PRD - See SUPER-DUPER-PLAN.md for detailed technical design*
