# Multi-Agent Support - Feature Matrix & Decision Document

**Date:** 2026-02-28
**Status:** Proposed
**Context:** Post-Agent Handoff Service Implementation
**Goal:** Complete Phase 3 (Multi-Agent Support) to 100%

---

## Executive Summary

After implementing the Agent Handoff Service, 5 new specs are proposed to complete Phase 3 Multi-Agent Support. This document captures the decision matrix, technical analysis, and implementation roadmap.

**Current Phase 3 Status: 85% → Target: 100%**

---

## Feature Decision Matrix

| # | Spec Name | Priority | Complexity | Dependencies | Risk | Duration | Status |
|---|-----------|----------|------------|--------------|------|----------|--------|
| 1 | Seamless Handoff Integration | ⭐⭐⭐⭐⭐ | LOW | None | LOW | 2-3 days | **FIRST** |
| 2 | Agent Communication Bus | ⭐⭐⭐ | MEDIUM | Spec 1 | MEDIUM | 1 week | WEEK 5-6 |
| 3 | Parallel Execution Coordinator | ⭐⭐ | HIGH | Spec 1+2 | HIGH | 2 weeks | WEEK 7+ |
| 4 | Specialist Agent Router | ⭐⭐⭐ | MEDIUM | None | LOW | 1 week | WEEK 3-4 |
| 5 | Multi-Agent Session Aggregation | ⭐⭐⭐⭐ | LOW | None | LOW | 1 day | **SECOND** |

**Note:** Spec numbers (1-5 above) are shorthand references. Actual spec files are numbered 12-16:
- Spec 1 = `docs/specs/12-seamless-handoff-integration.md`
- Spec 2 = `docs/specs/13-agent-communication-bus.md`
- Spec 3 = `docs/specs/14-parallel-execution-coordinator.md`
- Spec 4 = `docs/specs/15-specialist-agent-router.md`
- Spec 5 = `docs/specs/16-multi-agent-session-aggregation.md`

---

## Detailed Analysis by Spec

### Spec 1: Seamless Handoff Integration

**Decision:** ⭐ IMPLEMENT FIRST

**Decision Trace:**
1. Handoff service exists (completed 2026-02-28)
2. Only needs wiring to reassignment endpoint
3. Completes Phase 3 immediately
4. Enables all downstream specs
5. Zero new infrastructure

**Technical Feasibility:** HIGH
- Service: `backend/app/services/agent_handoff.py` ✅ EXISTS
- Endpoint: `backend/app/api/session_control.py` ✅ EXISTS
- Missing: Auto-trigger on reassign

**Implementation Options Considered:**

| Option | Description | Pros | Cons | Decision |
|--------|-------------|------|------|----------|
| A | Auto-handoff only | Simple | File-only storage | ❌ Not queryable |
| B | Auto + optional DB | Queryable history | Requires migration | ✅ **CHOSEN** |
| C | Manual trigger | User control | Easy to forget | ❌ Defeats purpose |
| D | Conditional | Saves resources | Complex logic | ❌ Over-engineering |

**Chosen Approach: B - Auto + Optional DB**

**Rationale:**
- Every reassign creates handoff (complete context)
- Stored in database for history/queries
- Opt-out flag available for quick reassigns
- Enables handoff analytics

**Files to Modify:**
```
backend/app/api/session_control.py  - Add auto-handoff to reassign endpoint
backend/app/models/handoff.py       - NEW: Database model
backend/app/services/agent_handoff.py  - Add DB storage
alembic/versions/XXX_add_handoffs.py   - NEW: Migration
frontend/src/components/portfolio/ProjectSessionPanel.tsx  - Show handoff indicator
```

---

### Spec 2: Agent Communication Bus

**Decision:** WEEK 5-6 (AFTER Spec 1+4+5)

**Decision Trace:**
1. High value for multi-agent coordination
2. Requires infrastructure decision
3. Blocks Spec 3 (parallel execution)
4. Multiple viable approaches

**Technical Feasibility:** MEDIUM

**Implementation Options Considered:**

| Option | Infrastructure | Pros | Cons | Decision |
|--------|----------------|------|------|----------|
| A | Full Redis pub/sub | Production-grade, scalable | New dependency, deployment complexity | ❌ Overkill for single-user |
| B | PostgreSQL NOTIFY | Uses existing DB | Less scalable, connection limits | ⚠️ Backup option |
| C | File-based queue | No new infra | Polling overhead, slow | ❌ Performance issue |
| D | WebSocket relay | Existing infra, simple | Less robust than Redis | ✅ **CHOSEN** |

**Chosen Approach: D - WebSocket Relay**

**Rationale:**
- Leverages existing WebSocket server
- No new infrastructure dependencies
- Sufficient for single-user deployment
- Can upgrade to Redis later if multi-tenant
- Faster implementation (1 week vs 2+ weeks)

**Architecture:**
```
Agent A → WebSocket Server → Agent B
         ↓
      Message Log (DB)
         ↓
      Frontend Display
```

**Files to Create:**
```
backend/app/services/agent_communication.py  - NEW: Communication service
backend/app/api/agent_messages.py            - NEW: Message endpoints
frontend/src/components/communication/AgentMessageLog.tsx  - NEW
```

---

### Spec 3: Parallel Execution Coordinator

**Decision:** WEEK 7+ (DEFERRABLE, MOST COMPLEX)

**Decision Trace:**
1. Highest complexity by far
2. Requires Spec 1 (handoff for failed items)
3. Requires Spec 2 (communication between agents)
4. Can operate without it in v1
5. User can manually split tasks for now

**Technical Feasibility:** LOW-MEDIUM

**Implementation Options Considered:**

| Option | Scope | Complexity | Pros | Cons | Decision |
|--------|-------|------------|------|------|----------|
| A | Manual work items | MEDIUM | User control, simple | No auto-split | ✅ **CHOSEN** |
| B | File-based splitting | MEDIUM | Automatic | Limited scope | ❌ Not flexible |
| C | AI decomposition | VERY HIGH | Full automation | Unproven, complex | ❌ Too risky |
| D | Test parallelization | LOW | Clear scope | Narrow use case | ❌ Too limited |

**Chosen Approach: A - Manual Work Items**

**Rationale:**
- User explicitly creates work items
- Agents claim available items
- Simple state machine: TODO → CLAIMED → DONE → FAILED
- Can add AI decomposition later
- Parallel execution with user control

**Work Item State Machine:**
```
    ┌─────────┐
    │  TODO   │ ◄───┐
    └────┬────┘     │
         │          │ (retry)
         ▼          │
    ┌─────────┐     │
    │ CLAIMED │     │
    └────┬────┘     │
         │          │
    ┌────┴────┐     │
    ▼         ▼     │
  ┌─────┐  ┌──────┐
  │ DONE │  │FAILED│
  └─────┘  └──────┘
```

**Files to Create:**
```
backend/app/models/work_item.py          - NEW: WorkItem model
backend/app/services/parallel_coord.py   - NEW: Coordinator
backend/app/api/work_items.py            - NEW: Work item endpoints
frontend/src/components/execution/ParallelExecutionView.tsx  - NEW
```

---

### Spec 4: Specialist Agent Router

**Decision:** WEEK 3-4 (INDEPENDENT, MEDIUM VALUE)

**Decision Trace:**
1. No dependencies on other specs
2. Adds intelligence to agent assignment
3. User-facing configuration
4. Medium complexity, clear value

**Technical Feasibility:** MEDIUM

**Implementation Options Considered:**

| Option | Classification | Complexity | Pros | Cons | Decision |
|--------|----------------|------------|------|------|----------|
| A | Rule-based | LOW | Deterministic | Brittle, maintenance | ❌ Too rigid |
| B | User hints | LOW | User control | Manual effort | ⚠️ Part of solution |
| C | ML classifier | HIGH | Adaptive | Training data, complexity | ❌ Over-engineering |
| D | Agent declaration | MEDIUM | Self-describing | Config required | ✅ **CHOSEN** |

**Chosen Approach: D + B - Agent Declaration + User Hints**

**Rationale:**
- Agents declare capabilities via config
- User can override with manual hints
- Simple classification rule engine
- Can add ML later if needed

**Capability Matching Algorithm:**
```
score(agent, task) =
    capability_match * 0.6 +
    current_load_penalty * 0.3 +
    affinity_bonus * 0.1
```

**Files to Create:**
```
backend/app/services/agent_router.py      - NEW: Router service
backend/app/models/agent_capabilities.py  - NEW: Capability model
backend/app/api/routing.py                - NEW: Routing endpoints
frontend/src/components/routing/SpecialistConfig.tsx  - NEW
```

---

### Spec 5: Multi-Agent Session Aggregation

**Decision:** ⭐ SECOND (QUICK WIN AFTER SPEC 1)

**Decision Trace:**
1. Lowest complexity
2. Immediate UX improvement
3. No dependencies
4. **FRONTEND-ONLY after discovery** - data already exists in dashboardStore!
5. Can be done in parallel with Spec 4

**Technical Feasibility:** HIGH

**KEY DISCOVERY:** The `dashboardStore.sessions[]` already contains all session data via WebSocket live updates! We just need to:
- Group sessions by project_id
- Aggregate metrics (counts, progress, agents)
- Display in UI component

**Implementation Options Considered:**

| Option | Scope | Backend | Frontend | Complexity | Decision |
|--------|-------|---------|----------|------------|----------|
| A | Project page only | New API endpoint | New component | MEDIUM | ❌ Overkill |
| B | Project page only | None - read existing | New component | LOW | ✅ **CHOSEN** |
| C | Real-time sync | WebSocket | Live component | HIGH | ❌ WebSocket already exists! |

**Chosen Approach: B - Frontend Aggregation Only**

**Rationale:**
- Add MultiAgentPanel component to project detail page
- Read from existing `dashboardStore.sessions[]`
- Aggregate by project_id (simple filter + reduce)
- No new API, no polling, no backend changes
- WebSocket already provides live updates

**Clarification:**
- **Original plan** was to add API endpoint + polling (Option A)
- **User question revealed** that WebSocket already sends all session data
- **Revised approach** uses existing data - simpler and faster!

**Why Only Per-Project:**
- Multi-agent coordination happens at project level
- Cross-project aggregation = portfolio management (Phase 2 scope)
- Single project focus = faster implementation, clear value

**Files to Create:**
- `frontend/src/components/portfolio/MultiAgentPanel.tsx` - NEW

**Files to Modify:**
- `frontend/src/app/projects/[id]/page.tsx` - Add MultiAgentPanel

**Files NOT Changed (originally planned):**
- ~~backend/app/api/portfolio.py~~ - No new endpoint needed
- ~~backend/app/models/~~ - No new models needed

---

## Implementation Roadmap

### Sprint 1: Foundation (Week 1-2)
```
┌─────────────────────────────────────────────────────────┐
│ Week 1-2: Spec 1 (Handoff Integration) + Spec 5 (Aggregation) │
├─────────────────────────────────────────────────────────┤
│ Day 1-2:  Database migration for handoffs               │
│ Day 3-4:  Modify reassign endpoint for auto-handoff     │
│ Day 5:    Frontend handoff indicator                    │
│ Day 6:    Spec 5: Create MultiAgentPanel component     │
│          - Read from dashboardStore.sessions           │
│          - Aggregate by project_id                     │
│          - Display metrics, timeline, heatmap           │
│ Day 7-8:  Testing, bug fixes                            │
│ Day 9:   Documentation                                 │
└─────────────────────────────────────────────────────────┘
Result: Phase 3 at 100%, immediate UX improvement
Note: Spec 5 simplified to frontend-only (1 day vs 2-3 days)
```

### Sprint 2: Intelligence (Week 3-4)
```
┌─────────────────────────────────────────────────────────┐
│ Week 3-4: Spec 4 (Specialist Router)                    │
├─────────────────────────────────────────────────────────┤
│ Day 1-2:  Agent capability config system                │
│ Day 3-4:  Routing algorithm implementation              │
│ Day 5-6:  Frontend specialist configuration UI           │
│ Day 7:    Testing with different agent types            │
│ Day 8:    Documentation                                 │
└─────────────────────────────────────────────────────────┘
Result: Intelligent agent assignment
```

### Sprint 3: Communication (Week 5-6)
```
┌─────────────────────────────────────────────────────────┐
│ Week 5-6: Spec 2 (Communication Bus - WebSocket)        │
├─────────────────────────────────────────────────────────┤
│ Day 1-2:  WebSocket message relay implementation        │
│ Day 3-4:  Message persistence and history               │
│ Day 5-6:  Frontend message log display                  │
│ Day 7:    Inter-agent messaging testing                 │
│ Day 8:    Documentation                                 │
└─────────────────────────────────────────────────────────┘
Result: Agents can communicate
```

### Sprint 4+: Parallel Execution (Week 7+)
```
┌─────────────────────────────────────────────────────────┐
│ Week 7+: Spec 3 (Parallel Execution)                    │
├─────────────────────────────────────────────────────────┤
│ Day 1-3:  Work item data model and state machine        │
│ Day 4-6:  Coordinator service and claiming logic        │
│ Day 7-9:  Conflict detection for shared files           │
│ Day 10-12: Frontend parallel execution view             │
│ Day 13-14: Testing with multiple agents                 │
└─────────────────────────────────────────────────────────┘
Result: Multiple agents per project
```

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Handoff DB migration fails | HIGH | LOW | Backup, rollback plan |
| WebSocket communication unreliable | MEDIUM | MEDIUM | Fallback to polling |
| Parallel execution conflicts | HIGH | MEDIUM | File locking, manual resolution |
| Specialist routing wrong decisions | LOW | HIGH | User override, learning |
| Session aggregation performance | LOW | LOW | Pagination, caching |

---

## Success Criteria

### Spec 1 (Handoff Integration):
- [ ] Every reassign creates handoff automatically
- [ ] Handoff stored in database
- [ ] Frontend shows handoff indicator
- [ ] Handoff history queryable via API

### Spec 2 (Communication Bus):
- [ ] Agents can send messages via WebSocket
- [ ] Message history persists to database
- [ ] Frontend displays message log
- [ ] Unavailable agents receive queued messages

### Spec 3 (Parallel Execution):
- [ ] User can create work items
- [ ] Agents can claim work items
- [ ] Conflict detection for shared files
- [ ] Progress aggregation across agents

### Spec 4 (Specialist Router):
- [ ] Agents declare capabilities
- [ ] Router suggests best agent
- [ ] User can override routing
- [ ] Routing improves over time

### Spec 5 (Session Aggregation):
- [ ] Project page shows all agent sessions
- [ ] Cross-agent timeline view
- [ ] Aggregated metrics display
- [ ] Multi-agent activity heatmap

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOPE-DASH ARCHITECTURE                    │
│                     (After All Specs Implemented)               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  Project Detail    │  Multi-Agent Panel  │  Specialist Config   │
│  (Spec 5)          │  (Spec 3)           │  (Spec 4)            │
│  ┌──────────────┐  │  ┌──────────────┐  │  ┌──────────────┐   │
│  │ Handoff View │  │  │ Work Items   │  │  │ Capabilities  │   │
│  │ Session List │  │  │ Progress     │  │  │ Routing Rules │   │
│  │ Timeline     │  │  │ Conflicts    │  │  │ Agent Pools  │   │
│  └──────────────┘  │  └──────────────┘  │  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ WebSocket + HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          API LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  /api/handoffs      │  /api/messages    │  /api/routing        │
│  (Spec 1)           │  (Spec 2)         │  (Spec 4)            │
│  - create           │  - send           │  - suggest           │
│  - list             │  - history        │  - override          │
│  - get              │  - subscribe      │  - config            │
├─────────────────────────────────────────────────────────────────┤
│  /api/work-items    │  /api/sessions    │                      │
│  (Spec 3)           │  (Spec 5)         │                      │
│  - create           │  - aggregate      │                      │
│  - claim            │  - timeline       │                      │
│  - complete         │  - metrics        │                      │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  AgentHandoffSvc   │  AgentCommBus     │  SpecialistRouter     │
│  (Spec 1)           │  (Spec 2)         │  (Spec 4)             │
│  - auto-create      │  - pub/sub        │  - capability-match   │
│  - DB storage       │  - history        │  - load-balance       │
├─────────────────────────────────────────────────────────────────┤
│  ParallelCoord      │  SessionAggregator│  AgentPoolSync        │
│  (Spec 3)           │  (Spec 5)         │  (Existing)           │
│  - work-item state  │  - cross-agent    │  - detection          │
│  - conflict detect  │  - timeline       │  - health-check       │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL               │  WebSocket Server  │  File System    │
│  - handoffs              │  - message relay   │  - handoff docs  │
│  - messages              │  - real-time       │  - work items    │
│  - work_items            │  - broadcasts      │                  │
│  - agent_capabilities    │                    │                  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       AGENT WRAPPERS                             │
├─────────────────────────────────────────────────────────────────┤
│  RalphWrapper  │  ClaudeWrapper  │  CursorWrapper  │  Terminal   │
│  ┌──────────┐  │  ┌──────────┐   │  ┌──────────┐   │  ┌────────┐ │
│  │ Detect   │  │  │ Detect   │   │  │ Detect   │   │  │ Detect │ │
│  │ Monitor  │  │  │ Monitor  │   │  │ Monitor  │   │  │ Monitor│ │
│  │ Control  │  │  │ Control  │   │  │ Control  │   │  │ Control│ │
│  │ Handoff  │  │  │ Handoff   │   │  │ Handoff  │   │  │ Handoff│ │
│  └──────────┘  │  └──────────┘   │  └──────────┘   │  └────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Revision Note: Spec 5 Simplified (2026-02-28)

**Original Plan:** Add new API endpoint + polling for session aggregation
**Revised Plan:** Frontend-only component using existing WebSocket data

**Why?** User question revealed that `dashboardStore.sessions[]` already contains all session data via WebSocket live updates. No new API needed - just aggregate and display!

**Changes:**
- Duration: 2-3 days → **1 day** (frontend component only)
- Complexity: LOW → **TRIVIAL** (read existing data, no backend changes)
- Files to create: 3 files → **1 file** (MultiAgentPanel.tsx)
- Backend changes: Required → **NONE**

This is a perfect example of collaborative refinement - asking "is this redundant?" led to a much simpler implementation.

---

## References

- **Handoff Service:** `backend/app/services/agent_handoff.py` (Implemented 2026-02-28)
- **Security Decisions:** `docs/plans/2026-02-28-security-architecture-decisions.md`
- **Phase 5 Plan:** `plans/001-ui-navigation-issue-fix.md`
- **Agent Handoff Plan:** `plans/004-agent-handoff-service-phase6.md`

---

**Document Version:** 1.0
**Last Updated:** 2026-02-28
**Next Review:** After Sprint 1 completion
