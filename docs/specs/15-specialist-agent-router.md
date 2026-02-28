# Spec 15: Specialist Agent Router

**Status:** Proposed
**Priority:** ⭐⭐⭐
**Complexity:** MEDIUM
**Duration:** 1 week
**Parent:** Phase 3 (Multi-Agent Support)
**Dependencies:** None

---

## Overview

### Objective

Route tasks to the most suitable agent based on task type and agent capabilities. Enable specialist agent pools (frontend, backend, testing, documentation) with intelligent matching.

### Problem Statement

Currently:
- Manual agent selection only
- No capability matching
- All agents treated as generalists
- No specialist configuration

After implementation:
- Agents declare capabilities
- Router suggests best agent
- User can override routing
- Specialist pools configured

### Success Criteria

- [ ] Agents can declare capabilities
- [ ] Router suggests best agent for task
- [ ] User can override routing decisions
- [ ] Specialist pools configurable via UI
- [ ] Capability scoring algorithm works

---

## Approach: Agent Declaration + User Hints

Agents declare capabilities via config. User provides hints for manual override. Simple rule-based scoring.

### Capability Scoring

```
score(agent, task) =
    capability_match * 0.6 +
    current_load_penalty * 0.3 +
    affinity_bonus * 0.1
```

---

## Database Schema

### New Table: `agent_capabilities`

```sql
CREATE TABLE agent_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) NOT NULL UNIQUE,

    -- Capabilities
    capabilities JSONB NOT NULL DEFAULT '{}',
    -- Example: {"frontend": 0.9, "backend": 0.7, "testing": 0.5}

    -- Specialist pools
    specialist_pools JSONB NOT NULL DEFAULT '[]',
    -- Example: ["frontend", "typescript"]

    -- Performance metrics
    avg_completion_time INTEGER,
    success_rate DECIMAL(3, 2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agent_capabilities_agent_id ON agent_capabilities(agent_id);
CREATE INDEX idx_agent_capabilities_pools ON agent_capabilities USING GIN(specialist_pools);
```

---

## API Implementation

### New Endpoint: `POST /api/routing/suggest`

```python
@router.post("/suggest", response_model=RoutingSuggestion)
async def suggest_agent(
    task_type: str,
    project_id: uuid.UUID,
    user_hints: list[str] | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> RoutingSuggestion:
    """Suggest best agent for a task.

    Args:
        task_type: Type of task (frontend, backend, testing, docs)
        project_id: Project context
        user_hints: Optional manual hints

    Returns:
        Routing suggestion with confidence score
    """
    from app.services.agent_router import AgentRouter

    router = AgentRouter(session)
    suggestion = await router.suggest_agent(task_type, project_id, user_hints)

    return suggestion
```

---

## Frontend: Specialist Config

```typescript
// frontend/src/components/routing/SpecialistConfig.tsx

export function SpecialistConfig() {
  return (
    <Card>
      <h2>Specialist Pools</h2>
      <PoolConfig name="frontend" agents={["ralph-1", "claude-2"]} />
      <PoolConfig name="backend" agents={["ralph-2"]} />
      <PoolConfig name="testing" agents={["cursor-1"]} />
    </Card>
  );
}
```

---

**Document Version:** 1.0
**Created:** 2026-02-28
**Status:** Ready for Implementation
