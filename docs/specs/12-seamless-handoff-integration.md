# Spec 12: Seamless Handoff Integration

**Status:** Proposed
**Priority:** ⭐⭐⭐⭐⭐ (FIRST)
**Complexity:** LOW
**Duration:** 2-3 days
**Parent:** Phase 3 (Multi-Agent Support)
**Dependencies:** None (builds on existing handoff service)

---

## Overview

### Objective

Integrate the existing Agent Handoff Service directly into the session reassignment flow. When a session is reassigned to a different agent, automatically create a handoff context that preserves:

- Tool usage summaries
- Files modified during the session
- Pending tasks
- Key decisions made
- Recent messages

Store handoffs in the database for queryability and history, with an opt-out flag for quick reassignments.

### Problem Statement

Currently:
- ✅ Handoff service exists (`agent_handoff.py`)
- ✅ Handoff API endpoints exist
- ❌ Session reassignment doesn't trigger handoff creation
- ❌ Handoffs only stored as files (not queryable)
- ❌ Frontend doesn't show handoff status

After implementation:
- ✅ Every reassign creates handoff automatically
- ✅ Handoffs stored in database
- ✅ Frontend shows handoff indicator
- ✅ Handoff history queryable via API

### Success Criteria

- [ ] Session reassignment automatically creates handoff
- [ ] Handoff stored in `handoffs` table
- [ ] Frontend shows handoff indicator on reassigned sessions
- [ ] Handoff history queryable via `GET /api/handoffs`
- [ ] Opt-out flag works for quick reassignments
- [ ] All tests pass (unit + integration)

---

## Architecture

### Approach: Auto + Optional DB

**Decision:** Every reassign creates handoff by default, stored in database. User can opt-out with `skip_handoff=true` query parameter.

**Rationale:**
- Complete context preservation by default
- Database storage enables history/queries
- Opt-out available for quick reassignments
- Minimal code changes (service already exists)

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION REASSIGNMENT FLOW                    │
└─────────────────────────────────────────────────────────────────┘

  User Request                          Backend Process
  ─────────────                          ────────────────

  POST /api/sessions/{id}/reassign
  ├── new_agent_type: "CLAUDE"
  ├── new_agent_id: "claude-1"
  └── skip_handoff: false (default)
              │
              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ session_control.py::reassign_session()                       │
  ├─────────────────────────────────────────────────────────────┤
  │ 1. Validate session state                                    │
  │ 2. Validate agent availability (SELECT FOR UPDATE)           │
  │ 3. IF NOT skip_handoff:                                      │
  │    → Create handoff context via agent_handoff service        │
  │    → Store handoff in database                               │
  │ 4. Update session agent assignment                          │
  │ 5. Update agent pool loads                                   │
  └─────────────────────────────────────────────────────────────┘
              │
              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ agent_handoff.py::create_handoff()                           │
  ├─────────────────────────────────────────────────────────────┤
  │ 1. Get SummaryCollector for session                          │
  │ 2. Create HandoffContext with collected data                 │
  │ 3. Store to database (NEW)                                   │
  │ 4. Store to disk (existing)                                  │
  └─────────────────────────────────────────────────────────────┘
              │
              ▼
  Response: {
    "id": "session-uuid",
    "handoff_id": "handoff-uuid",  // NEW
    "handoff_created": true,
    "message": "Session reassigned with handoff"
  }
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│  ProjectSessionPanel.tsx                                       │
│  ├── Session Card                                               │
│  │   ├── Agent Status                                           │
│  │   ├── Session Status                                         │
│  │   └── Handoff Badge (NEW) ─────────────────────┐            │
│  └── Reassign Dialog                                   │            │
│      ├── Agent Selection                                │            │
│      ├── Skip Handoff Checkbox (NEW)                    │            │
│      └── Reassign Button                                 │            │
└─────────────────────────────────────────────────────────┼─────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│  session_control.py::reassign_session()                         │
│  ├── Validate                                                   │
│  ├── Create handoff (NEW)                                       │
│  ├── Update session                                             │
│  └── Return response with handoff_id                            │
└─────────────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  agent_handoff.py::create_handoff()                             │
│  ├── Collect summary from SummaryCollector                      │
│  ├── Create HandoffContext                                      │
│  ├── Store to DB (NEW) ──────────────────────────────┐          │
│  └── Store to disk                                    │          │
└─────────────────────────────────────────────────────────┼─────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL - handoffs Table (NEW)                              │
│  ├── id (UUID, PK)                                             │
│  ├── session_id (UUID, FK)                                     │
│  ├── source_agent_type                                         │
│  ├── source_agent_id                                           │
│  ├── target_agent_type                                         │
│  ├── target_agent_id                                           │
│  ├── summary (TEXT)                                            │
│  ├── tool_summaries (JSONB)                                    │
│  ├── files_modified (JSONB)                                    │
│  ├── pending_tasks (JSONB)                                     │
│  ├── decisions (JSONB)                                         │
│  ├── recent_messages (JSONB)                                   │
│  ├── created_at (TIMESTAMP)                                    │
│  └── metadata (JSONB)                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### New Table: `handoffs`

```sql
-- Migration: alembic/versions/20250228_001_add_handoffs_table.py

CREATE TABLE handoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Source agent info
    source_agent_type VARCHAR(50) NOT NULL,
    source_agent_id VARCHAR(255) NOT NULL,

    -- Target agent info
    target_agent_type VARCHAR(50) NOT NULL,
    target_agent_id VARCHAR(255) NOT NULL,

    -- Handoff content
    summary TEXT NOT NULL,
    tool_summaries JSONB NOT NULL DEFAULT '[]',
    files_modified JSONB NOT NULL DEFAULT '[]',
    pending_tasks JSONB NOT NULL DEFAULT '[]',
    decisions JSONB NOT NULL DEFAULT '[]',
    recent_messages JSONB NOT NULL DEFAULT '[]',

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'
);

-- Indexes for common queries
CREATE INDEX idx_handoffs_session_id ON handoffs(session_id);
CREATE INDEX idx_handoffs_source_agent ON handoffs(source_agent_id);
CREATE INDEX idx_handoffs_target_agent ON handoffs(target_agent_id);
CREATE INDEX idx_handoffs_created_at ON handoffs(created_at DESC);

-- Composite index for session handoff history
CREATE INDEX idx_handoffs_session_created ON handoffs(session_id, created_at DESC);
```

### Migration File

```python
# alembic/versions/20250228_001_add_handoffs_table.py

"""add handoffs table

Revision ID: 20250228_001
Revises: <previous_revision>
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20250228_001'
down_revision = '<previous_revision_id>'  # Update this
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create handoffs table with indexes."""
    op.create_table(
        'handoffs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('source_agent_type', sa.String(length=50), nullable=False),
        sa.Column('source_agent_id', sa.String(length=255), nullable=False),
        sa.Column('target_agent_type', sa.String(length=50), nullable=False),
        sa.Column('target_agent_id', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('tool_summaries', postgresql.JSONB(), nullable=False),
        sa.Column('files_modified', postgresql.JSONB(), nullable=False),
        sa.Column('pending_tasks', postgresql.JSONB(), nullable=False),
        sa.Column('decisions', postgresql.JSONB(), nullable=False),
        sa.Column('recent_messages', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_handoffs_session_id', 'handoffs', ['session_id'])
    op.create_index('idx_handoffs_source_agent', 'handoffs', ['source_agent_id'])
    op.create_index('idx_handoffs_target_agent', 'handoffs', ['target_agent_id'])
    op.create_index('idx_handoffs_created_at', 'handoffs', ['created_at'])
    op.create_index('idx_handoffs_session_created', 'handoffs', ['session_id', 'created_at'])


def downgrade() -> None:
    """Drop handoffs table."""
    op.drop_index('idx_handoffs_session_created', 'handoffs')
    op.drop_index('idx_handoffs_created_at', 'handoffs')
    op.drop_index('idx_handoffs_target_agent', 'handoffs')
    op.drop_index('idx_handoffs_source_agent', 'handoffs')
    op.drop_index('idx_handoffs_session_id', 'handoffs')
    op.drop_table('handoffs')
```

---

## API Changes

### Modified Endpoint: `POST /api/sessions/{session_id}/reassign`

**Location:** `backend/app/api/session_control.py`

**Changes:**
- Add `skip_handoff` query parameter (default: false)
- Call handoff service before reassigning
- Return `handoff_id` in response

**New Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip_handoff` | boolean | No | false | Skip handoff creation for quick reassign |

**New Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `handoff_id` | string \| null | Handoff ID if created, null if skipped |
| `handoff_created` | boolean | Whether handoff was created |

**Updated Response Example:**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "agent_type": "claude",
  "message": "Session reassigned successfully",
  "assigned_agent_id": "claude-1",
  "previous_agent_type": "ralph",
  "handoff_id": "550e8400-e29b-41d4-a716-446655440000",
  "handoff_created": true
}
```

### Implementation Code

```python
# backend/app/api/session_control.py

@router.post("/{session_id}/reassign", response_model=dict[str, Any])
async def reassign_session(
    session_id: uuid.UUID,
    new_agent_type: AgentType | None = Query(None, description="New agent type to assign"),
    new_agent_id: str | None = Query(None, description="Specific agent ID to assign to"),
    skip_handoff: bool = Query(False, description="Skip handoff creation"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reassign a session to a different agent.

    Reassigns the session to run on a different agent.
    Only PAUSED or RUNNING sessions can be reassigned.

    This endpoint:
    - Validates the target agent exists and is available
    - Creates handoff context (unless skip_handoff=true)
    - Updates agent pool loads (decrements old, increments new)
    - Tracks reassignment history in session metadata

    Args:
        session_id: UUID of the session to reassign
        new_agent_type: Type of agent to reassign to
        new_agent_id: Specific agent ID to reassign to
        skip_handoff: Skip handoff creation for quick reassignment
        session: Database session

    Returns:
        Updated session information with handoff details

    Raises:
        HTTPException: If session not found, not in valid state, or agent unavailable
    """
    from sqlalchemy import update
    from app.models.agent_pool import AgentPool, PoolAgentStatus
    from app.services.agent_handoff import get_agent_handoff_service

    db_session = await session.get(Session, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.status not in (SessionStatus.PAUSED, SessionStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reassign session in {db_session.status.value} state. Pause first."
        )

    # Store previous type BEFORE any updates
    previous_agent_type = db_session.agent_type.value
    handoff_id = None
    handoff_created = False

    # Step 1: Create handoff if not skipped
    if not skip_handoff and (new_agent_type or new_agent_id):
        try:
            service = get_agent_handoff_service()

            # Get source agent info from session metadata
            metadata = db_session.meta_data or {}
            source_agent_id = metadata.get("assigned_agent_id", db_session.agent_type.value)

            # Determine target agent info
            target_type = (new_agent_type or db_session.agent_type).value
            target_id = new_agent_id or source_agent_id

            # Create a default summary if none exists
            summary = metadata.get("handoff_summary", "Session reassigned")

            context = await service.create_handoff(
                session_id=str(session_id),
                source_agent_type=db_session.agent_type.value,
                source_agent_id=source_agent_id,
                target_agent_type=target_type,
                target_agent_id=target_id,
                summary=summary,
            )

            # Store handoff in database (NEW)
            from db.models.handoff import Handoff
            from datetime import datetime, timezone

            db_handoff = Handoff(
                id=uuid.UUID(context.id),
                session_id=session_id,
                source_agent_type=context.source_agent_type,
                source_agent_id=context.source_agent_id,
                target_agent_type=context.target_agent_type,
                target_agent_id=context.target_agent_id,
                summary=context.summary,
                tool_summaries=[ts.to_dict() for ts in context.tool_summaries],
                files_modified=context.files_modified,
                pending_tasks=context.pending_tasks,
                decisions=context.decisions,
                recent_messages=context.recent_messages,
                created_at=context.created_at,
                metadata={"created_via": "reassign_endpoint"}
            )
            session.add(db_handoff)
            await session.flush()  # Flush to get handoff_id

            handoff_id = str(db_handoff.id)
            handoff_created = True

            logger.info(f"Created handoff {handoff_id} for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to create handoff for session {session_id}: {e}")
            # Continue with reassignment even if handoff fails
            handoff_created = False

    # Step 2: Validate and update agent pool if specifying a specific agent
    if new_agent_id:
        # Use SELECT FOR UPDATE to prevent race conditions
        agent_result = await session.execute(
            select(AgentPool)
            .where(
                AgentPool.agent_id == new_agent_id,
                AgentPool.deleted_at.is_(None),
            )
            .with_for_update()
        )
        agent = agent_result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{new_agent_id}' not found in pool"
            )

        if agent.status not in (PoolAgentStatus.AVAILABLE, PoolAgentStatus.BUSY):
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{new_agent_id}' is {agent.status.value} (must be available or busy)"
            )

        # Check capacity AFTER acquiring lock
        if agent.current_load >= agent.max_capacity:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{new_agent_id}' is at full capacity ({agent.current_load}/{agent.max_capacity})"
            )

        # Get the old agent ID from metadata
        old_agent_id = db_session.meta_data.get("assigned_agent_id") if db_session.meta_data else None

        # Decrement old agent's load if different from new agent
        if old_agent_id and old_agent_id != new_agent_id:
            old_agent_result = await session.execute(
                select(AgentPool)
                .where(AgentPool.agent_id == old_agent_id)
                .with_for_update()
            )
            old_agent = old_agent_result.scalar_one_or_none()
            if old_agent and old_agent.current_load > 0:
                old_agent.current_load -= 1
                if old_agent.current_load == 0 and old_agent.status == PoolAgentStatus.BUSY:
                    old_agent.status = PoolAgentStatus.AVAILABLE

        # Increment new agent's load
        agent.current_load += 1
        if agent.current_load >= agent.max_capacity:
            agent.status = PoolAgentStatus.BUSY
        agent.total_assigned += 1

    # Step 3: Update agent type if specified
    if new_agent_type:
        db_session.agent_type = new_agent_type

    # Step 4: Store reassignment info in metadata
    metadata = db_session.meta_data or {}
    metadata["reassigned"] = True
    metadata["previous_agent_type"] = previous_agent_type
    metadata["last_reassigned_at"] = datetime.now(timezone.utc).isoformat()
    if handoff_id:
        metadata["last_handoff_id"] = handoff_id
    if new_agent_id:
        metadata["assigned_agent_id"] = new_agent_id
    db_session.meta_data = metadata

    await session.commit()
    await session.refresh(db_session)

    logger.info(
        f"Session {session_id} reassigned to {new_agent_type or 'same type'} "
        f"(agent: {new_agent_id or 'any'}, handoff: {handoff_id})"
    )

    return {
        "id": str(db_session.id),
        "status": db_session.status.value,
        "agent_type": db_session.agent_type.value,
        "message": "Session reassigned successfully",
        "assigned_agent_id": new_agent_id,
        "previous_agent_type": previous_agent_type,
        "handoff_id": handoff_id,
        "handoff_created": handoff_created,
    }
```

---

## Frontend Changes

### Modified Component: `ProjectSessionPanel.tsx`

**Location:** `frontend/src/components/portfolio/ProjectSessionPanel.tsx`

**Changes:**
1. Add handoff badge to session cards
2. Add "Skip Handoff" checkbox to reassign dialog
3. Show handoff confirmation after reassign

### New Component: `HandoffBadge.tsx`

**Location:** `frontend/src/components/portfolio/HandoffBadge.tsx` (NEW)

```typescript
// frontend/src/components/portfolio/HandoffBadge.tsx

import { Tooltip } from "@/components/ui/tooltip";

interface HandoffBadgeProps {
  handoffId: string | null;
  createdAt?: string;
}

export function HandoffBadge({ handoffId, createdAt }: HandoffBadgeProps) {
  if (!handoffId) {
    return null;
  }

  const date = createdAt ? new Date(createdAt).toLocaleTimeString() : "Recent";

  return (
    <Tooltip content={`Handoff created at ${date}`}>
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
        <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M7 2a1 1 0 00-.707 1.707L7 4.414v3.758a1 1 0 01-.293.707l-4 4C.817 14.769 2.156 18 4.828 18h10.343c2.673 0 4.012-3.231 2.122-5.121l-4-4A1 1 0 0113 8.172V4.414l.707-.707A1 1 0 0013 2H7zm2 6.172V4h2v4.172a3 3 0 00.879 2.12l1.027 1.028a4 4 0 00-2.171.102l-.47.156a4 4 0 01-2.53 0l-.563-.187a1.993 1.993 0 00-.114-.035l1.063-1.063A3 3 0 009 8.172z" clipRule="evenodd" />
        </svg>
        Handoff
      </span>
    </Tooltip>
  );
}
```

### Modified: Reassign Dialog

```typescript
// In ProjectSessionPanel.tsx - Reassign Dialog

function ReassignDialog({ session, onReassign }: ReassignDialogProps) {
  const [skipHandoff, setSkipHandoff] = useState(false);
  // ... existing state

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reassign Session</DialogTitle>
        </DialogHeader>

        {/* Existing agent selection UI */}

        {/* NEW: Skip handoff checkbox */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="skip-handoff"
            checked={skipHandoff}
            onCheckedChange={setSkipHandoff}
          />
          <label htmlFor="skip-handoff" className="text-sm">
            Skip handoff (quick reassign)
          </label>
          <Tooltip content="Uncheck to preserve session context during handoff">
            <InfoIcon className="w-4 h-4 text-muted-foreground" />
          </Tooltip>
        </div>

        <DialogFooter>
          <Button onClick={() => onReassign(selectedAgent, skipHandoff)}>
            Reassign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### TypeScript Types

```typescript
// frontend/src/types/index.ts - Add to existing types

export interface SessionWithHandoff extends Session {
  last_handoff_id?: string;
  handoff_created?: boolean;
}

export interface HandoffRecord {
  id: string;
  session_id: string;
  source_agent_type: string;
  source_agent_id: string;
  target_agent_type: string;
  target_agent_id: string;
  summary: string;
  tool_summaries: ToolSummary[];
  files_modified: string[];
  pending_tasks: string[];
  decisions: string[];
  recent_messages: Message[];
  created_at: string;
  metadata: Record<string, unknown>;
}
```

---

## Database Model

### New File: `backend/app/models/handoff.py`

```python
# backend/app/models/handoff.py

"""Handoff database model."""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from db.connection import Base


class Handoff(Base):
    """Database model for agent handoff records."""

    __tablename__ = "handoffs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Source agent info
    source_agent_type = Column(String(50), nullable=False)
    source_agent_id = Column(String(255), nullable=False, index=True)

    # Target agent info
    target_agent_type = Column(String(50), nullable=False)
    target_agent_id = Column(String(255), nullable=False, index=True)

    # Handoff content
    summary = Column(Text, nullable=False)
    tool_summaries = Column(JSONB, nullable=False, default=list)
    files_modified = Column(JSONB, nullable=False, default=list)
    pending_tasks = Column(JSONB, nullable=False, default=list)
    decisions = Column(JSONB, nullable=False, default=list)
    recent_messages = Column(JSONB, nullable=False, default=list)

    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    metadata = Column(JSONB, nullable=False, default=dict)

    # Relationships
    session = relationship("Session", back_populates="handoffs")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "source_agent_type": self.source_agent_type,
            "source_agent_id": self.source_agent_id,
            "target_agent_type": self.target_agent_type,
            "target_agent_id": self.target_agent_id,
            "summary": self.summary,
            "tool_summaries": self.tool_summaries,
            "files_modified": self.files_modified,
            "pending_tasks": self.pending_tasks,
            "decisions": self.decisions,
            "recent_messages": self.recent_messages,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
```

### Update Session Model

```python
# backend/app/models/session.py - Add relationship

from sqlalchemy.orm import relationship
from typing import List

class Session(Base):
    # ... existing fields ...

    # NEW: Relationship to handoffs
    handoffs: List["Handoff"] = relationship(
        "Handoff",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="desc(Handoff.created_at)"
    )
```

---

## Service Changes

### Modified: `agent_handoff.py`

**Location:** `backend/app/services/agent_handoff.py`

**Changes:**
- Add database storage option to `_store_handoff()`
- Add `store_in_db` parameter to `create_handoff()`

```python
# In AgentHandoffService class

async def create_handoff(
    self,
    session_id: str,
    source_agent_type: str,
    source_agent_id: str,
    target_agent_type: str,
    target_agent_id: str,
    summary: str,
    store_in_db: bool = False,  # NEW parameter
    db_session: AsyncSession | None = None,  # NEW parameter
) -> HandoffContext:
    """Create a handoff context for a session transfer.

    Args:
        session_id: The session being transferred
        source_agent_type: Type of the source agent
        source_agent_id: ID of the source agent
        target_agent_type: Type of the target agent
        target_agent_id: ID of the target agent
        summary: Summary of work done so far
        store_in_db: Whether to store in database (NEW)
        db_session: Database session for DB storage (NEW)

    Returns:
        HandoffContext with collected data
    """
    collector = self.get_collector(session_id)

    context = HandoffContext(
        session_id=session_id,
        source_agent_type=source_agent_type,
        source_agent_id=source_agent_id,
        target_agent_type=target_agent_type,
        target_agent_id=target_agent_id,
        summary=summary,
        tool_summaries=collector.get_summaries(),
        files_modified=collector.get_files_modified(),
        pending_tasks=collector.get_pending_tasks(),
        decisions=collector.get_decisions(),
        recent_messages=collector.get_recent_messages(),
    )

    # Store the handoff
    await self._store_handoff(context, store_in_db=store_in_db, db_session=db_session)

    # Clear the collector after handoff
    self.clear_collector(session_id)

    logger.info(
        f"Created handoff context for session {session_id}: "
        f"{source_agent_type} → {target_agent_type}"
    )

    return context


async def _store_handoff(
    self,
    context: HandoffContext,
    store_in_db: bool = False,
    db_session: AsyncSession | None = None,
) -> None:
    """Store a handoff context to disk and optionally database.

    Args:
        context: The handoff context to store
        store_in_db: Whether to store in database (NEW)
        db_session: Database session for DB storage (NEW)
    """
    # Store markdown to disk
    markdown = generate_handoff_markdown(context)
    handoff_file = self._storage_dir / f"handoff-{context.id}.md"
    handoff_file.write_text(markdown, encoding="utf-8")

    # Store JSON to disk
    json_file = self._storage_dir / f"handoff-{context.id}.json"
    json_file.write_text(json.dumps(context.to_dict(), indent=2), encoding="utf-8")

    # NEW: Store to database if requested
    if store_in_db and db_session:
        from app.models.handoff import Handoff

        db_handoff = Handoff(
            id=uuid.UUID(context.id),
            session_id=uuid.UUID(context.session_id),
            source_agent_type=context.source_agent_type,
            source_agent_id=context.source_agent_id,
            target_agent_type=context.target_agent_type,
            target_agent_id=context.target_agent_id,
            summary=context.summary,
            tool_summaries=[ts.to_dict() for ts in context.tool_summaries],
            files_modified=context.files_modified,
            pending_tasks=context.pending_tasks,
            decisions=context.decisions,
            recent_messages=context.recent_messages,
            created_at=context.created_at,
        )
        db_session.add(db_handoff)

        logger.debug(f"Stored handoff to database: {context.id}")
    else:
        logger.debug(f"Stored handoff to disk: {handoff_file}")
```

---

## Testing Checklist

### Unit Tests

```python
# tests/test_services/test_agent_handoff.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.agent_handoff import AgentHandoffService, HandoffContext

@pytest.mark.asyncio
async def test_create_handoff_with_db_storage():
    """Test handoff creation with database storage."""
    service = AgentHandoffService()

    # Mock database session
    db_session = AsyncMock()
    db_session.add = MagicMock()
    db_session.flush = AsyncMock()

    context = await service.create_handoff(
        session_id="test-session-id",
        source_agent_type="RALPH",
        source_agent_id="ralph-1",
        target_agent_type="CLAUDE",
        target_agent_id="claude-1",
        summary="Test summary",
        store_in_db=True,
        db_session=db_session,
    )

    assert context.source_agent_type == "RALPH"
    assert context.target_agent_type == "CLAUDE"
    assert context.summary == "Test summary"
    db_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_handoff_skip_db():
    """Test handoff creation without database storage."""
    service = AgentHandoffService()

    context = await service.create_handoff(
        session_id="test-session-id",
        source_agent_type="RALPH",
        source_agent_id="ralph-1",
        target_agent_type="CLAUDE",
        target_agent_id="claude-1",
        summary="Test summary",
        store_in_db=False,
    )

    assert context.source_agent_type == "RALPH"
    assert context.target_agent_type == "CLAUDE"
```

### Integration Tests

```python
# tests/test_api/test_session_control.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_reassign_with_handoff(async_client: AsyncClient, test_session):
    """Test session reassignment creates handoff."""
    response = await async_client.post(
        f"/api/sessions/{test_session.id}/reassign",
        params={
            "new_agent_type": "CLAUDE",
            "new_agent_id": "claude-1",
            "skip_handoff": False,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["handoff_created"] is True
    assert data["handoff_id"] is not None


@pytest.mark.asyncio
async def test_reassign_skip_handoff(async_client: AsyncClient, test_session):
    """Test session reassignment skips handoff when requested."""
    response = await async_client.post(
        f"/api/sessions/{test_session.id}/reassign",
        params={
            "new_agent_type": "CLAUDE",
            "skip_handoff": True,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["handoff_created"] is False
    assert data["handoff_id"] is None
```

### Frontend Tests

```typescript
// tests/components/ProjectSessionPanel.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import { ProjectSessionPanel } from "@/components/portfolio/ProjectSessionPanel";

describe("ProjectSessionPanel", () => {
  it("shows handoff badge when session has handoff", () => {
    render(
      <ProjectSessionPanel
        sessions={[
          {
            id: "123",
            last_handoff_id: "handoff-456",
            // ... other fields
          },
        ]}
      />
    );

    expect(screen.getByText("Handoff")).toBeInTheDocument();
  });

  it("does not show handoff badge when no handoff", () => {
    render(
      <ProjectSessionPanel
        sessions={[
          {
            id: "123",
            // ... no handoff_id
          },
        ]}
      />
    );

    expect(screen.queryByText("Handoff")).not.toBeInTheDocument();
  });
});
```

### Manual Testing

- [ ] Reassign session with handoff, verify handoff_id in response
- [ ] Reassign session with skip_handoff=true, verify no handoff created
- [ ] Check handoff appears in frontend session card
- [ ] Query handoff history via API
- [ ] Verify database handoffs table populated
- [ ] Check handoff files still created in disk
- [ ] Test rollback with alembic downgrade

---

## Rollback Plan

### Database Rollback

```bash
# If migration causes issues
alembic downgrade -1

# Verify table dropped
psql -d dope_dash -c "\dt handoffs"

# Verify indexes dropped
psql -d dope_dash -c "\di"
```

### Code Rollback

```bash
# Revert to pre-implementation commit
git revert <commit-hash>

# Or reset to known-good state
git reset --hard <pre-implementation-tag>
```

### Verification Steps After Rollback

1. Sessions can still be reassigned
2. No handoff_id in response
3. No errors in logs
4. Frontend loads without errors

---

## Migration Steps

### Pre-Deployment

1. **Backup database**
   ```bash
   pg_dump dope_dash > backup_$(date +%Y%m%d).sql
   ```

2. **Review migration**
   ```bash
   alembic review 20250228_001_add_handoffs_table.py
   ```

3. **Test migration on staging**
   ```bash
   alembic upgrade head --sql
   ```

### Deployment

1. **Stop backend**
   ```bash
   systemctl stop dope-dash-backend
   ```

2. **Run migration**
   ```bash
   alembic upgrade head
   ```

3. **Verify schema**
   ```bash
   psql -d dope_dash -c "\d handoffs"
   ```

4. **Start backend**
   ```bash
   systemctl start dope-dash-backend
   ```

5. **Verify health**
   ```bash
   curl http://localhost:8000/api/health
   ```

---

## Monitoring

### Metrics to Track

- Handoff creation rate (per hour)
- Handoff storage failure rate
- Reassign time with/without handoff
- Database query performance for handoffs

### Logging

```python
# Add structured logging
logger.info(
    "handoff_created",
    extra={
        "handoff_id": handoff_id,
        "session_id": session_id,
        "source_agent": source_agent_id,
        "target_agent": target_agent_id,
        "duration_ms": duration,
    }
)
```

### Alerts

- Handoff creation failure rate > 5%
- Handoff DB query time > 500ms
- Handoff file storage failures

---

## Documentation

### API Documentation

Update OpenAPI spec with new parameter:

```yaml
/api/sessions/{session_id}/reassign:
  post:
    parameters:
      - name: skip_handoff
        in: query
        schema:
          type: boolean
          default: false
        description: Skip handoff creation for quick reassignment
    responses:
      200:
        content:
          application/json:
            schema:
              properties:
                handoff_id:
                  type: string
                  nullable: true
                handoff_created:
                  type: boolean
```

### User Documentation

Update user guide with handoff feature:

```markdown
## Session Reassignment

When reassigning a session to a different agent, Dope-Dash automatically creates a **handoff document** that preserves:

- Tool usage history
- Files modified
- Pending tasks
- Key decisions
- Recent messages

### Quick Reassign

For quick reassignments without handoff, check "Skip handoff" in the reassign dialog.

### Handoff History

View all handoffs for a session in the session detail panel.
```

---

## References

- **Handoff Service:** `backend/app/services/agent_handoff.py`
- **Security Decisions:** `docs/plans/2026-02-28-security-architecture-decisions.md`
- **Matrix Document:** `docs/plans/2026-02-28-multi-agent-support-matrix.md`
- **Session Control API:** `backend/app/api/session_control.py`

---

**Document Version:** 1.0
**Created:** 2026-02-28
**Author:** Claude (via brainstorming + writing-plans skill)
**Status:** Ready for Implementation
