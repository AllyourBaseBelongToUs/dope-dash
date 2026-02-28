# Security & Architecture Decisions Design Doc

**Date:** 2026-02-28
**Status:** Approved
**Context:** Deferred issues from Agent Handoff Service implementation

---

## Context

During implementation of the Agent Handoff Service, four architectural decisions were deferred:

1. Authentication approach
2. API naming convention (camelCase vs snake_case)
3. Audit logging strategy
4. File read optimization for handoffs

This document captures the decisions made through collaborative brainstorming.

---

## Deployment Context

**Primary user:** Single user (developer)
**Access methods:**
- Local laptop (localhost)
- Phone via Tailscale (local network)
- Remote access via Tailscale (traveling)
- Remote VMs via SSH or Tailscale

**Key insight:** Tailscale provides network-level security. The dashboard is never exposed to public internet.

---

## Decision 1: Authentication

### Choice: Optional / Minimal

**Rationale:**
- Tailscale mesh network already provides isolation
- No public internet exposure
- Single user scenario
- API key optional for programmatic access

### Implementation:

```python
# Optional: Simple API key for programmatic access
# Stored in environment variable or config file
API_KEY = os.getenv("DOPE_DASH_API_KEY")

# Middleware checks API key only if configured
@app.middleware("http")
async def optional_auth(request, call_next):
    if API_KEY and request.url.path.startswith("/api/"):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith(f"Bearer {API_KEY}"):
            # Only enforce if API_KEY is set
            pass
    return await call_next(request)
```

### Future considerations:
- Add API key if exposing endpoints to scripts/automation
- Keep Tailscale as primary security layer

---

## Decision 2: API Naming Convention

### Choice: camelCase from Backend

**Rationale:**
- Frontend naturally uses camelCase (JavaScript/TypeScript)
- Current codebase has transformation functions in service layer
- Cleaner code = less maintenance
- Pydantic aliases make this trivial

### Implementation:

```python
# Pydantic model with aliases
from pydantic import BaseModel, Field

class HandoffResponse(BaseModel):
    id: str
    session_id: str = Field(alias="sessionId")
    source_agent_type: str = Field(alias="sourceAgentType")
    source_agent_id: str = Field(alias="sourceAgentId")
    target_agent_type: str = Field(alias="targetAgentType")
    target_agent_id: str = Field(alias="targetAgentId")
    created_at: str = Field(alias="createdAt")

    class Config:
        populate_by_name = True  # Accept both names
        alias_generator = lambda x: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(x.split('_'))
        )
```

### Migration strategy:
1. **New endpoints** → Use camelCase aliases from start
2. **Existing endpoints** → Add aliases when working on those files
3. **Service layer** → Remove transformation code incrementally
4. **No big refactor** → Steady improvement over time

### Example before/after:

**Before (current):**
```typescript
// Service transformation
agentId: data.agent_id,
agentType: data.agent_type,
currentProjectId: data.current_project_id,
```

**After (target):**
```typescript
// Direct use, no transformation
const { agentId, agentType, currentProjectId } = data;
```

---

## Decision 3: Audit Logging

### Choice: Configurable Levels, Detailed by Default

**Rationale:**
- Start detailed, dial down when stable
- Observability feature, not security feature
- Runtime configurable without restart
- Useful for debugging and understanding system behavior

### Log Levels:

| Level | What it tracks | Storage |
|-------|----------------|---------|
| `minimal` | Action type + timestamp | Session metadata |
| `standard` | + Source (device/API key) | Session metadata |
| `detailed` | + Before/after state diff | Separate audit table |
| `full` | Immutable event log | Event sourcing pattern |

### Configuration:

```python
# Stored in database or config file
class AuditConfig(BaseModel):
    level: str = "detailed"  # minimal, standard, detailed, full
    retention_days: int = 30
    include_state_diff: bool = True
    include_request_metadata: bool = True
```

### API endpoint for runtime config:

```python
@router.patch("/api/settings/audit")
async def update_audit_config(config: AuditConfigUpdate):
    """Update audit logging level at runtime."""
    # Update config in database
    # No restart required
```

### Audit log entry structure:

```python
class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime
    action: str  # pause, resume, reassign, handoff_create, etc.
    resource_type: str  # session, project, agent
    resource_id: str
    source: str  # localhost, phone, script, etc.
    user_agent: str | None
    ip_address: str | None  # Tailscale IP
    before_state: dict | None  # For detailed/full
    after_state: dict | None   # For detailed/full
    metadata: dict
```

### Default: Start with `detailed`
- Captures state changes for debugging
- Can dial down to `standard` once stable
- `full` available for troubleshooting specific issues

---

## Decision 4: File Read Optimization

### Choice: Lazy Loading with Limit of 100

**Rationale:**
- Only read files we actually need
- Scales better for large datasets
- Simple to implement

### Implementation:

```python
async def list_handoffs(
    self,
    session_id: str | None = None,
    source_agent_id: str | None = None,
    target_agent_id: str | None = None,
    limit: int = 100,  # Changed from 50
    offset: int = 0,
) -> list[dict]:
    """List handoff contexts with lazy loading."""

    # Step 1: Get file list only (no reading)
    files = sorted(
        self._storage_dir.glob("handoff-*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    # Step 2: Apply offset and limit BEFORE reading
    files_to_read = files[offset:offset + limit]

    # Step 3: Read and parse only needed files
    handoffs = []
    for json_file in files_to_read:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))

            # Apply filters
            if session_id and data.get("session_id") != session_id:
                continue
            if source_agent_id and data.get("source_agent_id") != source_agent_id:
                continue
            if target_agent_id and data.get("target_agent_id") != target_agent_id:
                continue

            handoffs.append(self._summarize(data))

        except Exception as e:
            logger.warning(f"Failed to read {json_file}: {e}")

    return handoffs
```

### Performance comparison:

| Files | Old approach | Lazy loading |
|-------|--------------|--------------|
| 100 | Read 100 | Read 100 |
| 1000 | Read 1000 | Read 100 |
| 10000 | Read 10000 | Read 100 |

---

## Implementation Checklist

### Phase 1: File Read Optimization
- [ ] Implement lazy loading in `list_handoffs()`
- [ ] Change default limit to 100
- [ ] Add offset parameter for pagination

### Phase 2: API Naming
- [ ] Add Pydantic alias generator to base response models
- [ ] Update new handoff endpoints with aliases
- [ ] Document alias pattern for future endpoints

### Phase 3: Audit Logging
- [ ] Create `audit_log` table
- [ ] Add `AuditConfig` model
- [ ] Add audit middleware
- [ ] Add runtime config endpoint
- [ ] Start with `detailed` level

### Phase 4: Optional Auth
- [ ] Add optional API key middleware
- [ ] Add `DOPE_DASH_API_KEY` env var support
- [ ] Document Tailscale security model

---

## Files to Create/Modify

### New Files
- `backend/app/models/audit.py` - Audit log model
- `backend/app/models/config.py` - Runtime configuration models
- `backend/app/api/settings.py` - Settings API endpoints

### Modified Files
- `backend/app/services/agent_handoff.py` - Lazy loading
- `backend/app/api/session_control.py` - Pydantic aliases, audit logging
- `backend/app/main.py` - Optional auth middleware

---

## References

- Tailscale security: https://tailscale.com/kb/1016/security
- Pydantic aliases: https://docs.pydantic.dev/latest/concepts/alias/
- Lazy loading patterns: https://python-patterns.guide/python/patterns/lazy_loading/
