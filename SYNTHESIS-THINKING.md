# Synthesis Thinking - Super Duper Plan Creation

**AOT Session:** 2026-01-23
**Method:** Sequential Thinking (mcp_st_sequentialthinking)
**Total Thoughts:** 8
**Purpose:** Synthesize all research and design into cohesive implementation plan

---

## Thought Chain

### Thought 1: Research Review
**Input:** All completed atoms (mcp-feedback research, port architecture, query interface, control/feedback integration)

**Key Findings:**
- Persistent Session Model - single monitoring session across specs
- Real-Time Bidirectional Communication - WebSocket events
- Intelligent Environment Detection - auto VM vs local
- Multi-Modal State Management - session history, audio alerts
- Hierarchical Timeout Management - per-spec → session → cleanup
- Port architecture: 8001-8003 for monitoring, 3000-3099 for dev servers
- Query interface: Simple commands + Claude Code integration
- Control integration: MVP → Enhanced → Polish phases

**Insight:** All components are independent and can be integrated into a cohesive system.

---

### Thought 2: Optimal Architecture Determination
**Analysis:** THREE LAYERS identified:

1. **Presentation Layer** (Dashboard on Windows)
   - Next.js dashboard on port 8003
   - WebSocket client for real-time updates
   - Query interface for text commands
   - Audio alerts for notifications

2. **API Layer** (On VM)
   - WebSocket server on port 8001 (bidirectional)
   - REST API on port 8002 (query interface)
   - PostgreSQL on localhost:5432 (persistence)

3. **Instrumentation Layer** (Wrapped around Ralph)
   - SessionManager - tracks progress across specs
   - TimeoutManager - prevents hung builds
   - StateManager - persists session history
   - EnvironmentDetector - auto-configures based on context

**Critical Integration Point:** Ralph's existing output needs to be captured and transformed into WebSocket events. The tmux pipe-pane approach from research doc is perfect for this.

**Port Conflict Resolution:**
- Dev servers: localhost binding (3000-3099 range)
- Monitoring: explicit IP binding (8001-8003 range)
- No overlap possible

---

### Thought 3: Claude Code Integration Strategy
**Question:** Can the dashboard query Claude Code with text prompts?

**Answer:** YES but in different ways:

**Querying Ralph:**
- Direct via ralph-query commands (status, error, logs, tokens, eta)
- Indirect via dashboard UI (buttons, filters)
- Intervention commands (skip, stop, pause, resume)

**Querying Claude Code:**
- Dashboard runs Claude Code CLI as subprocess on VM
- Example: "Explain CR-02 failure" → `claude "why did CR-02 fail"` executed on VM
- Response captured and returned to dashboard
- Displayed in formatted UI

**Key Insight:** The dashboard becomes a UNIFIED interface for BOTH Ralph AND Claude Code. You can monitor autonomous builds AND ask contextual questions without switching tools.

**Architecture:**
1. Dashboard sends query to Monitoring API
2. Monitoring API spawns Claude Code process on VM
3. Captures Claude Code output (stdout/stderr)
4. Returns result to dashboard via WebSocket
5. Dashboard displays formatted response

---

### Thought 4: Additional Features Brainstorming
**Question:** What ELSE would make this dashboard exceptional?

**Features Identified:**

1. **Multi-Ralph Orchestration**
   - Dashboard manages MULTIPLE Ralph sessions on different projects
   - Each project gets its own tmux session, WebSocket channel
   - Unified view: "3 Ralph sessions running, 12 specs total across projects"

2. **Spec Dependency Visualization**
   - Ralph specs have dependencies (some must run before others)
   - Dashboard shows dependency graph
   - Visual progress through dependency tree

3. **Cost & Token Analytics**
   - Real-time token usage tracking
   - Cost projection: "This session will cost ~$2.50 total"
   - Historical cost trends per project

4. **Comparison & Regression Detection**
   - Compare current run vs previous runs
   - "Spec 05 took 2x longer than last time"
   - Test failure rate trending

5. **Automated Reporting**
   - Generate PDF/Markdown summary after each session
   - Email/Slack notification on completion
   - "Nightly build succeeded: 11/11 specs, 0 failures"

6. **Intervention Recommendations**
   - AI analyzes failures and suggests actions
   - "CR-02 failed 3 times, recommended: skip and continue"
   - "Token budget 80% used, recommended: pause for review"

**Most Valuable:** Multi-Ralph orchestration, Cost analytics, Automated reporting

---

### Thought 5: Implementation Strategy
**Analysis:** Need to prioritize VALUE while managing COMPLEXITY.

**Phased Rollout Strategy:**

**Phase 1 (MVP - Week 1):** "Can I see what's happening?"
- Single Ralph session monitoring
- WebSocket events (Ralph → Dashboard)
- Basic UI: progress bar, current spec, status
- Port architecture setup (8001-8003)
- **Value:** Real-time visibility into overnight builds

**Phase 2 (Control - Week 2):** "Can I influence what's happening?"
- Bidirectional WebSocket (Dashboard → Ralph)
- Query interface (ralph-query commands)
- Basic interventions: pause, resume, skip
- Error notifications
- **Value:** Can correct course without SSH

**Phase 3 (Enhanced - Week 3):** "Can I understand and optimize?"
- Claude Code integration (ask questions about failures)
- Session history and comparison
- Cost/token analytics
- Multi-Ralph orchestration
- **Value:** Deep insights, multi-project management

**Phase 4 (Polish - Week 4):** "Can I set it and forget it?"
- Automated reporting (PDF/Markdown summaries)
- Environment detection (VM vs local)
- Audio alerts
- SSH tunnel setup automation
- **Value:** True overnight automation, minimal intervention

**Total:** ~4 weeks to fully-featured system

---

### Thought 6: Technical Integration Details
**Focus:** How all components actually connect. This is where many projects fail.

**Critical Integration Points:**

1. **Ralph Output Capture**
   - Ralph writes to stdout/stderr
   - tmux pipe-pane captures to log file
   - Log tailer script reads new lines
   - Parser extracts structured events
   - WebSocket broadcaster pushes to dashboard
   - **Challenge:** Parsing unstructured output into events

2. **State Persistence**
   - SessionManager lives in memory (lost on crash)
   - StateManager persists to JSON every spec completion
   - Recovery: On restart, load last state from disk
   - **Challenge:** Handling crash mid-spec

3. **Query Interface Integration**
   - Dashboard sends query to API (port 8002)
   - API reads Ralph state files
   - For Claude Code queries: spawn subprocess, capture output
   - **Challenge:** Claude Code output is unstructured

4. **WebSocket Connection Management**
   - Dashboard auto-reconnects on disconnect
   - Server tracks connected clients
   - Heartbeat from Ralph every 10s
   - **Challenge:** Detecting stale connections

**BIGGEST Risk:** Ralph output parser - if Ralph changes output format, everything breaks.

**Solution:** Use Ralph's existing structured output (JSON summary files) as source of truth, not parse stdout.

---

### Thought 7: File Structure & Technology Stack
**Decision:** Make this concrete so user knows EXACTLY what will be built.

**Technology Stack (Confirmed):**
- VM Backend: Python (FastAPI for WebSocket/API)
- Database: PostgreSQL 17 (already researched)
- Dashboard: Next.js 15 + React 19 + TypeScript
- Real-time: WebSocket (native, no libraries needed)
- State: JSON files for history, in-memory for active session

**File Structure:**
```
ralph-inferno/
├── monitoring/                    # Python backend
│   ├── api/                       # FastAPI application
│   ├── managers/                  # Core business logic
│   └── integrations/              # External integrations
├── dashboard/                     # Next.js frontend
│   ├── src/
│   │   ├── app/                   # Next.js 15 App Router
│   │   ├── components/            # React components
│   │   └── lib/                   # Clients
└── .ralph/
    └── sessions/                  # Session history storage
```

Clear, follows conventions, separates concerns properly.

---

### Thought 8: Final Synthesis
**Integration:** Complete "Super Duper Plan" that combines all components.

**Complete Vision:**
A unified dashboard that monitors multiple autonomous Ralph sessions, provides real-time visibility, enables interventions, integrates Claude Code for contextual queries, and runs entirely on the VM with access from Windows via explicit IP bindings.

**Key Decisions Made:**
1. Port architecture: 8001-8003 for monitoring, 3000-3099 for dev servers
2. Data source: Ralph's existing JSON files (not parsing stdout)
3. Technology: Python FastAPI backend, Next.js frontend, PostgreSQL
4. Phased rollout: 4 weeks from MVP to production-ready
5. Claude Code integration: subprocess wrapper, not direct API
6. Multi-Ralph support: Designed into architecture from day 1

**What the user gets:**
- Week 1: Real-time monitoring dashboard
- Week 2: Control capabilities
- Week 3: Deep insights (Claude Code, analytics)
- Week 4: Production polish

**Risk Mitigation:**
- Use Ralph's structured output (JSON) - won't break on format changes
- WebSocket with polling fallback - works through any firewall
- Session persistence - survives crashes
- Port separation - zero conflicts

**Conclusion:** This plan is actionable, technically sound, and delivers incremental value.

---

## Success Criteria

✅ All atoms synthesized into cohesive plan
✅ Technical integration details documented
✅ Implementation phases clearly defined
✅ Risk mitigation strategies identified
✅ File structure and technology stack confirmed
✅ Ready to present to user

---

## Output Files

- Main plan: `.taskmaster/docs/plans/SUPER-DUPER-PLAN.md`
