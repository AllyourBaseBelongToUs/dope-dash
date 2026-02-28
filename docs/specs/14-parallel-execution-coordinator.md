# Spec 14: Parallel Execution Coordinator

**Status:** Proposed
**Priority:** ⭐⭐
**Complexity:** HIGH
**Duration:** 2 weeks
**Parent:** Phase 3 (Multi-Agent Support)
**Dependencies:** Spec 1 (Handoff), Spec 2 (Communication)

---

## Overview

### Objective

Enable multiple agents to work on the same project simultaneously with automatic task coordination. Users create work items, agents claim them, progress is aggregated.

### Problem Statement

Currently:
- One agent per session
- No parallel execution
- No work item tracking
- No conflict detection

After implementation:
- User creates work items
- Agents claim available items
- Conflict detection for shared files
- Progress aggregation

### Success Criteria

- [ ] User can create work items
- [ ] Agents can claim work items
- [ ] Conflict detection for shared files
- [ ] Progress aggregated across agents
- [ ] Frontend parallel execution view

---

## Approach: Manual Work Items

**Decision:** User explicitly creates work items. Agents claim them. Simple state machine. Can add AI decomposition later.

### Work Item State Machine

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
  ┌─────┐  ┌──────┐ │
  │ DONE │  │FAILED│ │
  └─────┘  └──────┘ │
                    │
  ┌─────────────────┘
  ▼
(Optional:CANCELLED)
```

---

## Database Schema

### New Table: `work_items`

```sql
CREATE TABLE work_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_item_id UUID REFERENCES work_items(id) ON DELETE SET NULL,

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    task_type VARCHAR(50), -- feature, bug, test, docs, refactor

    -- State
    status VARCHAR(50) NOT NULL DEFAULT 'todo', -- todo, claimed, done, failed, cancelled
    priority INTEGER DEFAULT 5,

    -- Assignment
    assigned_agent_id VARCHAR(255),
    assigned_at TIMESTAMP WITH TIME ZONE,

    -- Tracking
    files_modified JSONB NOT NULL DEFAULT '[]',
    dependencies JSONB NOT NULL DEFAULT '[]',
    estimated_hours INTEGER,

    -- Result
    result_summary TEXT,
    failure_reason TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_work_items_project ON work_items(project_id, status);
CREATE INDEX idx_work_items_assigned ON work_items(assigned_agent_id);
CREATE INDEX idx_work_items_parent ON work_items(parent_item_id);
```

---

## API Changes

### New Endpoints

```python
# backend/app/api/work_items.py

@router.post("/", response_model=WorkItem)
async def create_work_item(
    project_id: uuid.UUID,
    title: str,
    description: str | None = None,
    task_type: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> WorkItem:
    """Create a new work item."""
    ...

@router.post("/{item_id}/claim", response_model=WorkItem)
async def claim_work_item(
    item_id: uuid.UUID,
    agent_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> WorkItem:
    """Claim a work item for an agent."""
    ...

@router.post("/{item_id}/complete", response_model=WorkItem)
async def complete_work_item(
    item_id: uuid.UUID,
    result_summary: str,
    files_modified: list[str],
    session: AsyncSession = Depends(get_db_session),
) -> WorkItem:
    """Mark a work item as complete."""
    ...

@router.post("/{item_id}/fail", response_model=WorkItem)
async def fail_work_item(
    item_id: uuid.UUID,
    failure_reason: str,
    session: AsyncSession = Depends(get_db_session),
) -> WorkItem:
    """Mark a work item as failed (requeueable)."""
    ...
```

---

## Conflict Detection

```python
# backend/app/services/parallel_coord.py

async def check_file_conflicts(
    work_item_id: uuid.UUID,
    files: list[str],
    session: AsyncSession,
) -> list[Conflict]:
    """Check if files are being modified by other work items."""
    conflicts = []

    # Find other claimed items with same files
    other_items = await session.execute(
        select(WorkItem)
        .where(
            WorkItem.status == "claimed",
            WorkItem.id != work_item_id,
            WorkItem.files_modified.overlap(files),
        )
    )

    for item in other_items.scalars():
        conflicts.append({
            "work_item_id": str(item.id),
            "agent_id": item.assigned_agent_id,
            "conflicting_files": list(set(files) & set(item.files_modified)),
        })

    return conflicts
```

---

## Frontend: Parallel Execution View

```typescript
// frontend/src/components/execution/ParallelExecutionView.tsx

export function ParallelExecutionView({ projectId }: { projectId: string }) {
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);

  return (
    <Card>
      <div className="flex justify-between items-center mb-4">
        <h2>Work Items</h2>
        <CreateWorkItemDialog projectId={projectId} />
      </div>

      <div className="space-y-2">
        {workItems.map((item) => (
          <WorkItemCard key={item.id} item={item} />
        ))}
      </div>

      <Progress value={calculateProgress(workItems)} />
    </Card>
  );
}

function WorkItemCard({ item }: { item: WorkItem }) {
  return (
    <Card className={`border-l-4 ${getStatusColor(item.status)}`}>
      <div className="flex justify-between">
        <h3>{item.title}</h3>
        <Badge>{item.status}</Badge>
      </div>
      {item.assigned_agent_id && (
        <p className="text-sm">Assigned to: {item.assigned_agent_id}</p>
      )}
      {item.files_modified.length > 0 && (
        <p className="text-sm">Files: {item.files_modified.join(", ")}</p>
      )}
    </Card>
  );
}
```

---

## Testing Checklist

- [ ] Create work item
- [ ] Claim work item
- [ ] Detect file conflicts
- [ ] Complete work item
- [ ] Fail and requeue work item
- [ ] Progress aggregation
- [ ] Dependency handling

---

**Document Version:** 1.0
**Created:** 2026-02-28
**Status:** Ready for Implementation
