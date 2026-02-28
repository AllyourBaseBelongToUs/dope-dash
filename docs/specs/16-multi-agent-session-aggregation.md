# Spec 16: Multi-Agent Session Aggregation (FRONTEND-ONLY)

**Status:** Revised
**Priority:** ⭐⭐⭐⭐ (SECOND)
**Complexity:** LOW
**Duration:** 1-2 days (frontend component only)
**Parent:** Phase 3 (Multi-Agent Support)
**Dependencies:** None

---

## Overview

### Objective

Create a unified view of multiple agents working on the same project by aggregating existing WebSocket session data. When multiple agents are assigned to different sessions within a project, provide:

- Aggregated metrics across all agents
- Cross-agent timeline visualization
- Multi-agent activity heatmap
- Project-level session overview

### Problem Statement

Currently:
- `dashboardStore.sessions[]` contains all sessions via WebSocket (live updates!)
- No project-level view to see all sessions grouped by project
- Hard to see coordination between agents on the same project
- Session data exists but not visualized per-project

### Solution: Frontend Aggregation

**The data already exists!** The WebSocket already pushes all sessions to `dashboardStore.sessions[]` in real-time. We just need to:

1. Group sessions by project
2. Aggregate metrics (counts, progress, active agents)
3. Display in a nice UI component

### Success Criteria

- [ ] MultiAgentPanel component displays sessions grouped by project
- [ ] Aggregated metrics computed from existing session data
- [ ] Cross-agent timeline from session timestamps
- [ ] Activity heatmap from session activity
- [ ] **No new API endpoint** - uses existing dashboardStore data

---

## Architecture

### Approach: Frontend Aggregation (No New API)

**Decision:** Read existing `dashboardStore.sessions[]` and aggregate by project. No new API endpoint, no polling. Data already comes via WebSocket live!

**Data Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND-ONLY AGGREGATION                    │
└─────────────────────────────────────────────────────────────────┘

  EXISTING WebSocket (already works!)
  ────────────────────────────────────────

  AGENTS → WEBSOCKET SERVER → FRONTEND
                      ↓
               dashboardStore:
                 - sessions[] ← ALL sessions, live updates!
                 - events[]

  NEW COMPONENT (to be created)
  ───────────────────────────────────────

  MultiAgentPanel:
    1. Read from dashboardStore.sessions[]
    2. Filter by project_id
    3. Aggregate metrics:
       - Count by status
       - Unique agents
       - Average progress
    4. Build timeline from session timestamps
    5. Show heatmap from activity

  NO POLLING! NO NEW API!
  Just read what's already there.
```

### Why This Works

| What We Need | Where It Comes From |
|---------------|---------------------|
| All sessions | `dashboardStore.sessions[]` (WebSocket) |
| Session status | `session.status` (running, paused, etc.) |
| Progress | `session.progress` (0-100) |
| Agent info | `session.agentType`, `session.metadata.agent_id` |
| Timestamps | `session.startedAt`, `session.lastActivity` |
| Events | `dashboardStore.events[]` (WebSocket) |

**Everything is already there!** We just need to visualize it.

---

---

## Implementation: Frontend Component Only

### Component: `MultiAgentPanel.tsx`

**Location:** `frontend/src/components/portfolio/MultiAgentPanel.tsx` (NEW)

```typescript
// frontend/src/components/portfolio/MultiAgentPanel.tsx

"use client";

import { useDashboardStore } from "@/store/dashboardStore";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface MultiAgentPanelProps {
  projectId: string;
}

export function MultiAgentPanel({ projectId }: MultiAgentPanelProps) {
  // Read from existing WebSocket data
  const { sessions } = useDashboardStore();

  // Aggregate by project (frontend computation!)
  const projectSessions = sessions.filter(s => s.metadata?.project_id === projectId);

  // Compute metrics
  const totalSessions = projectSessions.length;
  const activeSessions = projectSessions.filter(s => s.status === 'running').length;
  const pausedSessions = projectSessions.filter(s => s.status === 'paused').length;
  const completedSessions = projectSessions.filter(s => s.status === 'completed').length;

  // Get unique agents
  const agents = [...new Set(projectSessions.map(s => s.metadata?.assigned_agent_id).filter(Boolean))];
  const activeAgents = [...new Set(
    projectSessions
      .filter(s => s.status === 'running' || s.status === 'paused')
      .map(s => s.metadata?.assigned_agent_id)
      .filter(Boolean)
  )];

  // Combined progress
  const activeProgress = projectSessions
    .filter(s => s.status === 'running' || s.status === 'paused')
    .map(s => s.progress || 0);
  const combinedProgress = activeProgress.length > 0
    ? Math.round(activeProgress.reduce((a, b) => a + b, 0) / activeProgress.length)
    : 0;

  // Timeline (sort by lastActivity)
  const timeline = projectSessions
    .filter(s => s.lastActivity)
    .sort((a, b) => new Date(b.lastActivity!).getTime() - new Date(a.lastActivity!).getTime())
    .slice(0, 10)
    .map(s => ({
      timestamp: s.lastActivity!,
      sessionId: s.id,
      agentType: s.agentType,
      agentId: s.metadata?.assigned_agent_id || 'unassigned',
      status: s.status,
    }));

  // Heatmap data (last 7 days, by day)
  const heatmap = computeHeatmap(projectSessions);

  return (
    <Card className="p-6">
      <h2 className="text-xl font-semibold mb-4">Multi-Agent Overview</h2>

      {/* Metrics Grid */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard label="Total Sessions" value={totalSessions} />
        <MetricCard label="Active" value={activeSessions} />
        <MetricCard label="Paused" value={pausedSessions} />
        <MetricCard label="Completed" value={completedSessions} />
      </div>

      {/* Active Agents */}
      {activeAgents.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium mb-2">Active Agents ({activeAgents.length})</h3>
          <div className="flex flex-wrap gap-2">
            {activeAgents.map((agentId) => (
              <Badge key={agentId} variant="secondary">
                {agentId}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Combined Progress */}
      {activeSessions > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium mb-2">Combined Progress</h3>
          <Progress value={combinedProgress} />
          <p className="text-xs text-muted-foreground mt-1">{combinedProgress}%</p>
        </div>
      )}

      {/* Timeline */}
      {timeline.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium mb-2">Recent Activity</h3>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {timeline.map((event, idx) => (
              <div key={idx} className="text-sm flex items-center gap-2 text-muted-foreground">
                <span className="font-mono">{new Date(event.timestamp).toLocaleTimeString()}</span>
                <Badge variant="outline">{event.agentType}</Badge>
                <span className="capitalize">{event.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Heatmap */}
      {heatmap.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-2">Activity (Last 7 Days)</h3>
          <div className="flex gap-1">
            {heatmap.map((day) => (
              <div
                key={day.date}
                className="h-8 flex-1 rounded bg-blue-500 hover:bg-blue-600 transition-colors"
                style={{
                  opacity: Math.min(day.sessionCount / 5, 1),
                }}
                title={`${day.date}: ${day.sessionCount} sessions`}
              />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-4 bg-muted rounded-lg">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}

// Helper: Compute heatmap from sessions
function computeHeatmap(sessions: any[]) {
  const byDay = new Map<string, number>();

  for (const session of sessions) {
    if (!session.startedAt) continue;

    const date = new Date(session.startedAt).toISOString().split('T')[0];
    byDay.set(date, (byDay.get(date) || 0) + 1);
  }

  // Last 7 days
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split('T')[0];
    days.push({
      date: dateStr,
      sessionCount: byDay.get(dateStr) || 0,
    });
  }

  return days;
}
```

### Usage in Project Detail Page

```typescript
// In your project detail page

import { MultiAgentPanel } from "@/components/portfolio/MultiAgentPanel";
import { useDashboardStore } from "@/store/dashboardStore";

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const { sessions } = useDashboardStore();
  const projectId = params.id;

  return (
    <div>
      <h1>{projectName}</h1>

      {/* Just pass the project ID - component reads from dashboardStore */}
      <MultiAgentPanel projectId={projectId} />

      {/* Rest of your project page */}
    </div>
  );
}
```

---

## What Changed vs Original Spec

| Original (Complex) | Revised (Simple) |
|-------------------|------------------|
| New API endpoint `/api/projects/{id}/aggregate` | ❌ Removed - use existing data |
| Backend aggregation logic | ❌ Removed - compute in frontend |
| 30-second polling | ❌ Removed - WebSocket already live |
| Database queries | ❌ Removed - data already in memory |
| Frontend component only | ✅ Just create the UI |

---

## Files to Create/Modify

### New Files
- `frontend/src/components/portfolio/MultiAgentPanel.tsx` - The component

### Modified Files
- `frontend/src/app/projects/[id]/page.tsx` - Add MultiAgentPanel to project detail

### Files NOT Changed (no longer needed)
- ~~backend/app/api/portfolio.py~~ (no new endpoint)
- ~~backend/app/models/~~ (no new models)

---

## Testing Checklist

### Frontend Tests

```typescript
// tests/components/MultiAgentPanel.test.tsx

import { render, screen } from "@testing-library/react";
import { MultiAgentPanel } from "@/components/portfolio/MultiAgentPanel";

describe("MultiAgentPanel", () => {
  it("aggregates sessions by project", () => {
    // Mock dashboardStore with sessions for different projects
    const mockSessions = [
      { id: "1", metadata: { project_id: "project-a" }, status: "running", progress: 50, agentType: "RALPH" },
      { id: "2", metadata: { project_id: "project-a" }, status: "paused", progress: 30, agentType: "CLAUDE" },
      { id: "3", metadata: { project_id: "project-b" }, status: "running", progress: 80, agentType: "CURSOR" },
    ];

    // Render with project-a
    render(<MultiAgentPanel projectId="project-a" />);

    // Should show only project-a sessions
    expect(screen.getByText("Total Sessions")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument(); // 2 sessions for project-a
  });

  it("shows active agents correctly", () => {
    const mockSessions = [
      { id: "1", metadata: { project_id: "project-a", assigned_agent_id: "ralph-1" }, status: "running" },
      { id: "2", metadata: { project_id: "project-a", assigned_agent_id: "claude-2" }, status: "paused" },
    ];

    render(<MultiAgentPanel projectId="project-a" />);

    expect(screen.getByText("ralph-1")).toBeInTheDocument();
    expect(screen.getByText("claude-2")).toBeInTheDocument();
  });
});
```

### Manual Testing

- [ ] Navigate to project with multiple sessions
- [ ] Verify only that project's sessions are shown
- [ ] Check metrics update when sessions change status (via WebSocket)
- [ ] Verify timeline shows recent activity
- [ ] Check heatmap displays activity over last 7 days
- [ ] Test with project that has no sessions (should show zeros/empty)

---

## Rollback Plan

### Simple Rollback

Since this is frontend-only:
```bash
# Just delete the component
rm frontend/src/components/portfolio/MultiAgentPanel.tsx

# Or revert the commit
git revert <commit-hash>
```

### No database changes
No migrations needed.
No backend changes to rollback.

---

## Documentation

### User Documentation

Add to user guide:

```markdown
## Multi-Agent Projects

When multiple agents work on the same project sessions, the project detail page shows:

- **Total Sessions**: All sessions for this project
- **Active/Paused/Completed**: Status breakdown
- **Active Agents**: Which agents are currently working
- **Combined Progress**: Average progress across active sessions
- **Recent Activity**: Timeline of session activity
- **Activity Heatmap**: Visual representation of session activity over the last 7 days

The multi-agent panel updates automatically via WebSocket (no refresh needed).
```

---

## References

- **Existing WebSocket:** `backend/server/websocket.py` (already sends session updates)
- **Dashboard Store:** `frontend/src/store/dashboardStore.ts` (holds sessions[])
- **Use WebSocket Hook:** `frontend/src/hooks/useWebSocket.ts` (receives live data)

---

**Document Version:** 2.0 (Revised - Frontend Only)
**Created:** 2026-02-28
**Revised:** 2026-02-28 (Simplified to frontend aggregation)
**Status:** Ready for Implementation

### Option A: Project Page Only (CHOSEN ✅)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SINGLE PROJECT VIEW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Project: Dope-Dash                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Multi-Agent Panel (NEW)                     │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │  │
│  │  │ Ralph (3)   │ │ Claude (2)  │ │ Cursor (1)  │        │  │
│  │  │ Running: 1  │ │ Running: 2  │ │ Running: 0  │        │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘        │  │
│  │                                                           │  │
│  │  Timeline: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━            │  │
│  │            Ralph   Claude  Cursor                        │  │
│  │            ━━━     ━━━━━━━  ━                             │  │
│  │                                                           │  │
│  │  Heatmap:                                                │  │
│  │  10:00  ████████████                                     │  │
│  │  11:00  ██████████                                       │  │
│  │  12:00  ██████████████████                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Sessions List (filtered by project)                          │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Session 1  │ Ralph    │ Running │ 45% │ 2 agents active│  │
│  │ Session 2  │ Claude   │ Running │ 78% │                │  │
│  │ Session 3  │ Cursor   │ Paused  │ 23% │                │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Updates: Polling every 30 seconds
Scope: Single project
Realtime: No (historical view)
```

### Option B: Cross-Project Aggregation (NOT CHOSEN)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PORTFOLIO VIEW (Phase 2)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Portfolio Overview                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Multi-Project Aggregation                               │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │ Dope-Dash    │  │ Twitter-Arch │  │ Claude-Flow  │   │  │
│  │  │ 3 agents     │  │ 2 agents     │  │ 1 agent      │   │  │
│  │  │ 15 sessions  │  │ 8 sessions   │  │ 4 sessions   │   │  │
│  │  │ 67% progress │  │ 89% done    │  │ 23% started  │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  │                                                           │  │
│  │  Combined Timeline (all projects):                       │  │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━        │  │
│  │  DD     TA      CF        (DD = Dope-Dash)               │  │
│  │  ━━━    ━━      ━                                          │  │
│  │                                                           │  │
│  │  Global Agent Distribution:                              │  │
│  │  Ralph: ████████████ (13 sessions)                      │  │
│  │  Claude: ████████████████████ (18 sessions)             │  │
│  │  Cursor: ██████ (6 sessions)                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Updates: Polling every 30 seconds
Scope: All projects (portfolio)
Realtime: No (historical view)
Phase: Phase 2 (Portfolio Management)
```

### Option C: Real-Time Sync via WebSocket (NOT CHOSEN)

```
┌─────────────────────────────────────────────────────────────────┐
│                 REAL-TIME MULTI-AGENT VIEW                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Project: Dope-Dash                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Live Multi-Agent Monitoring                      │  │
│  │                                                           │  │
│  │  Connection: WEBSOCKET CONNECTED ◉                       │  │
│  │  Last Update: Just now (23ms ago)                        │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ Agent Status (REAL-TIME)                            ││  │
│  │  │ ┌─────────────────────────────────────────────────┐││  │
│  │  │ │ Ralph-1     ● Running  [████████░░] 80%         │││  │
│  │  │ │ Claude-2    ● Running  [██████████] 100%        │││  │
│  │  │ │ Cursor-1    ○ Paused   [████░░░░░░] 40%         │││  │
│  │  │ │ Ralph-2     ○ Idle                                │││  │
│  │  │ └─────────────────────────────────────────────────┘││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  │                                                           │  │
│  │  Live Event Stream:                                       │  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ 14:32:01  Ralph-1   STARTED  Session #1234          ││  │
│  │  │ 14:32:05  Claude-2  PROGRESS  Session #1199 → 95%   ││  │
│  │  │ 14:32:08  Ralph-1   FILE     src/app.tsx            ││  │
│  │  │ 14:32:12  Claude-2  COMPLETED Session #1199         ││  │
│  │  │ 14:32:15  Cursor-1  PAUSED    Session #1201         ││  │
│  │  │ [auto-scrolling...]                                  ││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Updates: WebSocket push (instant)
Scope: Single project
Realtime: Yes (live events)
Complexity: High (WebSocket management, reconnection, etc.)
```

---

## Why Option A (Not Realtime)?

### Clarification on "Realtime"

**Realtime** in this context means **WebSocket push** - instant updates when something changes.

**Option A uses polling** - the frontend requests updates every 30 seconds.

**Why polling is sufficient here:**

| Factor | Polling (Option A) | WebSocket (Option C) |
|--------|-------------------|---------------------|
| Data freshness | 30-second delay | Instant |
| Data type | Historical (sessions, events) | Live events |
| Change frequency | Sessions change slowly | Events happen fast |
| Infrastructure | Uses existing HTTP | Needs WebSocket setup |
| Complexity | Low | Medium-High |
| Battery usage | Predictable | Constant connection |

**Key insight:** Session aggregation shows **historical state** - what sessions exist, their status, progress. This data doesn't change rapidly. A 30-second delay is acceptable.

**WebSocket would be overkill** because:
- Session status changes infrequently (minutes between changes)
- We're not streaming live events
- Adding WebSocket complexity for slow-changing data is YAGNI

**When WebSocket makes sense:**
- Live event streaming (Option C shows this)
- Instant notifications needed
- Real-time collaboration

### Why Only Per-Project?

**Multi-agent coordination happens at project level.**

When would you use multiple agents on the same project?
- Parallel feature development
- Specialist agents (frontend, backend, testing)
- Code review while development continues
- Documentation while coding

**Cross-project aggregation (Option B) is portfolio management:**
- Shows all projects at a glance
- Higher-level view for resource allocation
- Belongs in Phase 2 (Portfolio Management)
- Different use case than project-level coordination

**Single project focus keeps scope tight:**
- Clear value proposition
- Faster to implement
- Can expand to cross-project later
- Right-sized for the problem

---

## API Changes

### New Endpoint: `GET /api/projects/{project_id}/aggregate`

**Location:** `backend/app/api/portfolio.py`

**Response Schema:**

```typescript
interface ProjectAggregation {
  project_id: string;
  project_name: string;

  // Session counts
  total_sessions: number;
  active_sessions: number;
  sessions_by_status: {
    running: number;
    paused: number;
    completed: number;
    failed: number;
    cancelled: number;
    aborted: number;
  };

  // Agent info
  total_agents: number;
  agents_active: string[];
  agents_by_type: {
    RALPH: number;
    CLAUDE: number;
    CURSOR: number;
    TERMINAL: number;
  };

  // Progress
  combined_progress: number;  // 0-100
  estimated_completion: string | null;  // ISO datetime

  // Timeline data
  timeline: TimelineEvent[];

  // Heatmap data
  heatmap: {
    date: string;  // YYYY-MM-DD
    agents: string[];  // Active agents that day
    session_count: number;
  }[];

  // Recent sessions
  recent_sessions: SessionSummary[];
}

interface TimelineEvent {
  timestamp: string;
  session_id: string;
  agent_id: string;
  agent_type: string;
  event_type: "created" | "started" | "paused" | "completed" | "failed";
  description: string;
}

interface SessionSummary {
  id: string;
  agent_type: string;
  agent_id: string;
  status: string;
  progress: number;
  created_at: string;
  updated_at: string;
}
```

### Implementation

```python
# backend/app/api/portfolio.py

@router.get("/{project_id}/aggregate", response_model=ProjectAggregation)
async def get_project_aggregation(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectAggregation:
    """Get multi-agent aggregation for a project.

    Returns aggregated metrics, timeline, heatmap data
    for all sessions within a project.

    Args:
        project_id: UUID of the project
        session: Database session

    Returns:
        ProjectAggregation with all multi-agent data

    Raises:
        HTTPException: If project not found
    """
    from sqlalchemy import select, func
    from app.models.session import Session, SessionStatus
    from app.models.agent_pool import AgentPool

    # Get project
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all sessions for project
    sessions_result = await session.execute(
        select(Session)
        .where(Session.project_id == project_id)
        .order_by(Session.created_at.desc())
    )
    sessions = sessions_result.scalars().all()

    if not sessions:
        return ProjectAggregation(
            project_id=str(project_id),
            project_name=project.name,
            total_sessions=0,
            active_sessions=0,
            sessions_by_status={},
            total_agents=0,
            agents_active=[],
            agents_by_type={},
            combined_progress=0,
            estimated_completion=None,
            timeline=[],
            heatmap=[],
            recent_sessions=[],
        )

    # Count sessions by status
    status_counts = {}
    for status in SessionStatus:
        count = sum(1 for s in sessions if s.status == status)
        if count > 0:
            status_counts[status.value] = count

    active_count = status_counts.get("running", 0) + status_counts.get("paused", 0)

    # Get unique agents
    agent_ids = set()
    agents_by_type = {"RALPH": 0, "CLAUDE": 0, "CURSOR": 0, "TERMINAL": 0}

    for s in sessions:
        metadata = s.meta_data or {}
        agent_id = metadata.get("assigned_agent_id")
        if agent_id:
            agent_ids.add(agent_id)
        agents_by_type[s.agent_type.value] += 1

    # Get currently active agents
    active_agents = []
    for s in sessions:
        if s.status in (SessionStatus.RUNNING, SessionStatus.PAUSED):
            metadata = s.meta_data or {}
            agent_id = metadata.get("assigned_agent_id")
            if agent_id and agent_id not in active_agents:
                active_agents.append(agent_id)

    # Calculate combined progress
    progress_sum = 0
    progress_count = 0
    for s in sessions:
        if s.status in (SessionStatus.RUNNING, SessionStatus.PAUSED):
            metadata = s.meta_data or {}
            progress = metadata.get("progress", 0)
            if isinstance(progress, (int, float)):
                progress_sum += progress
                progress_count += 1

    combined_progress = int(progress_sum / progress_count) if progress_count > 0 else 0

    # Build timeline
    timeline = []
    for s in sessions:
        metadata = s.meta_data or {}
        agent_id = metadata.get("assigned_agent_id", s.agent_type.value)

        timeline.append({
            "timestamp": s.created_at.isoformat(),
            "session_id": str(s.id),
            "agent_id": agent_id,
            "agent_type": s.agent_type.value,
            "event_type": "created",
            "description": f"Session created by {s.agent_type.value}",
        })

        if s.status == SessionStatus.COMPLETED and s.updated_at:
            timeline.append({
                "timestamp": s.updated_at.isoformat(),
                "session_id": str(s.id),
                "agent_id": agent_id,
                "agent_type": s.agent_type.value,
                "event_type": "completed",
                "description": f"Session completed",
            })

    timeline.sort(key=lambda x: x["timestamp"])

    # Build heatmap (last 30 days)
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict

    heatmap_data = defaultdict(lambda: {"agents": set(), "count": 0})
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    for s in sessions:
        if s.created_at < cutoff:
            continue

        date_key = s.created_at.strftime("%Y-%m-%d")
        metadata = s.meta_data or {}
        agent_id = metadata.get("assigned_agent_id", s.agent_type.value)

        heatmap_data[date_key]["agents"].add(agent_id)
        heatmap_data[date_key]["count"] += 1

    heatmap = [
        {
            "date": date,
            "agents": list(data["agents"]),
            "session_count": data["count"],
        }
        for date, data in sorted(heatmap_data.items())
    ]

    # Recent sessions
    recent_sessions = [
        {
            "id": str(s.id),
            "agent_type": s.agent_type.value,
            "agent_id": (s.meta_data or {}).get("assigned_agent_id", "unassigned"),
            "status": s.status.value,
            "progress": (s.meta_data or {}).get("progress", 0),
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions[:10]
    ]

    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "total_sessions": len(sessions),
        "active_sessions": active_count,
        "sessions_by_status": status_counts,
        "total_agents": len(agent_ids),
        "agents_active": active_agents,
        "agents_by_type": agents_by_type,
        "combined_progress": combined_progress,
        "estimated_completion": None,  # TODO: Calculate based on velocity
        "timeline": timeline[-50:],  # Last 50 events
        "heatmap": heatmap,
        "recent_sessions": recent_sessions,
    }
```

---

## Frontend Changes

### Modified: Project Detail Page

**Location:** `frontend/src/app/projects/[id]/page.tsx`

```typescript
// frontend/src/app/projects/[id]/page.tsx

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { MultiAgentPanel } from "@/components/portfolio/MultiAgentPanel";

interface ProjectAggregation {
  project_id: string;
  project_name: string;
  total_sessions: number;
  active_sessions: number;
  sessions_by_status: Record<string, number>;
  total_agents: number;
  agents_active: string[];
  agents_by_type: Record<string, number>;
  combined_progress: number;
  timeline: TimelineEvent[];
  heatmap: HeatmapData[];
  recent_sessions: SessionSummary[];
}

export default function ProjectDetailPage() {
  const params = useParams();
  const [aggregation, setAggregation] = useState<ProjectAggregation | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Poll every 30 seconds
    const fetchAggregation = async () => {
      try {
        const response = await fetch(`/api/projects/${params.id}/aggregate`);
        const data = await response.json();
        setAggregation(data);
      } catch (error) {
        console.error("Failed to fetch aggregation:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAggregation();
    const interval = setInterval(fetchAggregation, 30000);

    return () => clearInterval(interval);
  }, [params.id]);

  if (loading) return <div>Loading...</div>;
  if (!aggregation) return <div>Project not found</div>;

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-3xl font-bold mb-6">{aggregation.project_name}</h1>

      {/* NEW: Multi-Agent Panel */}
      <MultiAgentPanel aggregation={aggregation} />

      {/* Existing project content */}
    </div>
  );
}
```

### New Component: `MultiAgentPanel.tsx`

**Location:** `frontend/src/components/portfolio/MultiAgentPanel.tsx`

```typescript
// frontend/src/components/portfolio/MultiAgentPanel.tsx

"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface MultiAgentPanelProps {
  aggregation: ProjectAggregation;
}

export function MultiAgentPanel({ aggregation }: MultiAgentPanelProps) {
  return (
    <Card className="p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Multi-Agent Overview</h2>

      {/* Metrics Grid */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard label="Total Sessions" value={aggregation.total_sessions} />
        <MetricCard label="Active Sessions" value={aggregation.active_sessions} />
        <MetricCard label="Agents Active" value={aggregation.agents_active.length} />
        <MetricCard label="Progress" value={`${aggregation.combined_progress}%`} />
      </div>

      {/* Active Agents */}
      {aggregation.agents_active.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium mb-2">Active Agents</h3>
          <div className="flex flex-wrap gap-2">
            {aggregation.agents_active.map((agentId) => (
              <Badge key={agentId} variant="secondary">
                {agentId}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Combined Progress */}
      <div className="mb-6">
        <h3 className="text-sm font-medium mb-2">Combined Progress</h3>
        <Progress value={aggregation.combined_progress} />
      </div>

      {/* Timeline */}
      {aggregation.timeline.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium mb-2">Recent Activity</h3>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {aggregation.timeline.slice(-10).map((event, idx) => (
              <div key={idx} className="text-sm flex items-center gap-2">
                <span className="text-muted-foreground">{event.timestamp}</span>
                <Badge variant="outline">{event.agent_type}</Badge>
                <span>{event.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Heatmap (simplified) */}
      {aggregation.heatmap.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-2">Activity Heatmap (Last 30 Days)</h3>
          <div className="flex gap-1">
            {aggregation.heatmap.slice(-30).map((day) => (
              <div
                key={day.date}
                className="h-8 flex-1 rounded bg-blue-500 hover:bg-blue-600"
                style={{
                  opacity: Math.min(day.session_count / 5, 1),
                }}
                title={`${day.date}: ${day.session_count} sessions`}
              />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-4 bg-muted rounded-lg">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
```

---

## Testing Checklist

### Unit Tests

```python
# tests/test_api/test_portfolio.py

import pytest

@pytest.mark.asyncio
async def test_get_project_aggregation_no_sessions(async_client, test_project):
    """Test aggregation with no sessions returns zeros."""
    response = await async_client.get(f"/api/projects/{test_project.id}/aggregate")

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 0
    assert data["active_sessions"] == 0


@pytest.mark.asyncio
async def test_get_project_aggregation_with_sessions(async_client, test_project, test_sessions):
    """Test aggregation calculates metrics correctly."""
    response = await async_client.get(f"/api/projects/{test_project.id}/aggregate")

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == len(test_sessions)
    assert data["agents_by_type"]["RALPH"] >= 0
    assert len(data["timeline"]) > 0
```

### Manual Testing

- [ ] Navigate to project with multiple sessions
- [ ] Verify metrics display correctly
- [ ] Check active agents list
- [ ] Verify combined progress calculation
- [ ] Check timeline displays recent events
- [ ] Verify heatmap shows activity distribution
- [ ] Test polling (changes appear within 30s)

---

## Rollback Plan

### API Rollback

```bash
# Remove aggregation endpoint
git revert <commit-hash>

# Or manually delete endpoint from portfolio.py
```

### Frontend Rollback

```bash
# Remove MultiAgentPanel
git revert <commit-hash>
```

---

## Documentation

### User Documentation

Add to user guide:

```markdown
## Multi-Agent Projects

When multiple agents work on the same project, the project detail page shows:

- **Active Agents**: List of agents currently working on sessions
- **Combined Progress**: Overall progress across all active sessions
- **Recent Activity**: Timeline of events across all sessions
- **Activity Heatmap**: Visual representation of agent activity over time

The multi-agent panel updates every 30 seconds.
```

---

## References

- **Matrix Document:** `docs/plans/2026-02-28-multi-agent-support-matrix.md`
- **Portfolio API:** `backend/app/api/portfolio.py`
- **Session Model:** `backend/app/models/session.py`

---

**Document Version:** 1.0
**Created:** 2026-02-28
**Status:** Ready for Implementation
