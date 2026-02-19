# Dope-Dash - Product Requirements Document

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
- Uvicorn (ASGI server - direct service startup, NO DOCKER)

**Frontend:**
- Next.js 15 with React 19 and TypeScript
- Tailwind CSS
- WebSocket client (real-time updates with auto-retry)
- Polling client (on-demand updates with manual retry)
- Web Audio API (sound alerts)
- react-virtuoso (event list virtualization)

**Infrastructure:**
- PostgreSQL on port 5432 (source of truth)
- Redis cache on port 6379
- tmux for session management
- Network: Windows ↔ VM (192.168.206.128)
- Direct Python services (NO CONTAINERIZATION)

---

## Port Architecture (COMPLETED)

| Port | Purpose | Status | Binding | Service |
|------|---------|--------|---------|---------|
| 8000 | Core API (query, reports, retention, portfolio, projects) | ✅ COMPLETED | 0.0.0.0 | FastAPI via uvicorn |
| 8001 | WebSocket Server (real-time push) | ✅ COMPLETED | 0.0.0.0 | FastAPI via uvicorn |
| 8002 | Control API (agent commands) | ✅ COMPLETED | 0.0.0.0 | FastAPI via uvicorn |
| 8003 | Dashboard (Next.js frontend) | ✅ COMPLETED | 0.0.0.0 | next dev |
| 8004 | Analytics API (metrics and trends) | ✅ COMPLETED | 0.0.0.0 | FastAPI via uvicorn |
| 5432 | PostgreSQL | ✅ COMPLETED | 127.0.0.1 | postgres |
| 6379 | Redis Cache | ✅ COMPLETED | 127.0.0.1 | redis-server |

---

## Implementation Status

**Architecture - COMPLETED:**
- ✅ Microservices architecture fully implemented (5 services on ports 8000-8004)
- ✅ PostgreSQL database on port 5432 (database-first persistence)
- ✅ Redis cache on port 6379
- ✅ NO DOCKER - Direct Python services with uvicorn

**Frontend - COMPLETED:**
- ✅ Next.js 15 + React 19 dashboard
- ✅ Real-time WebSocket connection with auto-retry (every 3 min)
- ✅ Manual retry button when in polling mode
- ✅ Event list virtualization with react-virtuoso
- ✅ Notification settings (sound toggle, desktop toggle, preference levels)
- ✅ Command palette with keyboard shortcuts
- ✅ Full settings page with export/import, search, preview mode
- ✅ Environment detection (VM vs local)

**Backend - COMPLETED:**
- ✅ FastAPI backend services (ports 8000-8004)
- ✅ WebSocket server for real-time events
- ✅ Control API for agent commands
- ✅ Analytics API with caching
- ✅ Database connection pooling (15 pool + 5 overflow per service)
- ✅ Request caching and deduplication
- ✅ localStorage quota management

**Code Quality - COMPLETED:**
- ✅ 30/32 critique issues fixed (94%)
- ✅ TypeScript strict mode enforced
- ✅ ESLint enforced in builds
- ✅ Type consolidations completed
- ✅ Security fixes (path traversal, injection prevention)

---

## Success Criteria

- [x] Dashboard shows real-time spec progress for all agents (COMPLETED)
- [x] Can pause/resume/skip any agent from dashboard (COMPLETED)
- [x] Slash commands work (Ctrl+K command palette) (COMPLETED)
- [ ] Multi-agent control unified (Ralph + Claude + Cursor + Terminal) (PARTIAL - Ralph implemented)
- [x] Analytics show historical trends (30/90/365 days) (COMPLETED)
- [x] Notifications work (audio + desktop) (COMPLETED)
- [ ] Mission Control portfolio view manages multiple projects (TODO - Phase 5)
- [ ] Agent pool management with load balancing (TODO - Phase 5)
- [ ] Rate limits detected and handled with auto-retry (TODO - Phase 6)
- [ ] /quota command shows usage statistics (TODO - Phase 6)

---

## Out of Scope

- IDE integration (VS Code MCP) - Phase 7+
- Hardware tapper device (Stream Deck, MIDI) - Future
- Mobile app - Future
- Multi-user support - Future

---

*End of PRD - See SUPER-DUPER-PLAN.md for detailed technical design*
