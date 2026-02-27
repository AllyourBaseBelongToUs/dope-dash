# Plan: Agent Detection "Never Called" Fix

**Status:** RESEARCH REQUIRED (not implementation)
**Created:** 2025-02-20
**Type:** Research Plan

## Problem Statement

The `AgentDetector` service exists at `backend/app/services/agent_detector.py` but appears to never be called/instantiated in the application flow. This means:
- Agents are not automatically detected on startup
- The detection methods (tmux scan, process scan) are never executed
- The agent pool UI may show empty or stale data
- Manual agent registration is the only current method

## Current Implementation

### AgentDetector Service
Location: `backend/app/services/agent_detector.py`

**Detection Methods:**
1. `detect_all_agents()` - Scans for all active agents via tmux + process scan
2. `detect_agent(agent_type, project_dir)` - Detect specific agent type
3. `_scan_tmux_sessions()` - Scans tmux sessions for agent patterns
4. `_scan_processes()` - Scans running processes for agent binaries

**Supported Agent Types:**
- `RALPH` - Ralph Inferno (tmux-based)
- `CLAUDE` - Claude Code CLI
- `CURSOR` - Cursor IDE
- `TERMINAL` - Raw shell sessions

### Singleton Pattern
```python
_agent_detector: AgentDetector | None = None

def get_agent_detector() -> AgentDetector:
    global _agent_detector
    if _agent_detector is None:
        _agent_detector = AgentDetector()
    return _agent_detector
```

## Research Tasks

### Phase 1: Trace Call Graph
- [ ] Search entire codebase for `get_agent_detector` imports
- [ ] Search for `AgentDetector` class imports
- [ ] Check if `detect_all_agents` is called anywhere
- [ ] Check API endpoints that should trigger detection
- [ ] Review WebSocket handlers for detection calls

### Phase 2: Identify Integration Points
- [ ] Where SHOULD agent detection be called?
  - On server startup?
  - On WebSocket connect?
  - Periodically via background task?
  - On-demand via API endpoint?
- [ ] Review `backend/app/api/` endpoints for agent-related routes
- [ ] Check if `agent_pool` page has backend API support

### Phase 3: Review Agent Pool Architecture
- [ ] Read `specs/23-agent-pool.md` for intended design
- [ ] Check if there's a `/api/agents` or `/api/agent-pool` endpoint
- [ ] Review how frontend `agent-pool/page.tsx` fetches data
- [ ] Check `agentPoolStore.ts` for data flow

### Phase 4: Define Integration Strategy
- [ ] Determine best trigger for detection:
  - Startup lifespan event?
  - Scheduled background task?
  - API endpoint trigger?
  - WebSocket subscription?
- [ ] Design data flow: detection -> storage -> API -> frontend
- [ ] Consider caching strategy (already in AgentDetector)

## Files to Research

```
backend/app/services/agent_detector.py   # The detector service
backend/app/services/agent_registry.py   # Related registry?
backend/app/services/agent_factory.py    # Related factory?
backend/server/control.py                # Control API server
backend/app/api/                         # All API routes
specs/23-agent-pool.md                   # Agent Pool spec
frontend/src/app/agent-pool/page.tsx     # Frontend page
frontend/src/store/agentPoolStore.ts     # State management
```

## Grep Commands to Execute

```bash
# Find all references to agent detector
grep -r "agent_detector" backend/
grep -r "AgentDetector" backend/
grep -r "get_agent_detector" backend/

# Find agent-related API endpoints
grep -r "agent" backend/app/api/
grep -r "detect" backend/app/api/

# Find frontend agent pool calls
grep -r "agent" frontend/src/api/
grep -r "agentPool" frontend/src/
```

## Questions to Answer

1. Is there an agent pool API endpoint that should call detection?
2. Should detection run on server startup in lifespan?
3. Should detection run periodically as background task?
4. How does the frontend expect to receive detected agents?
5. Is there a database model for detected agents?

## CONFIRMED ROOT CAUSE

**The `detect_and_register()` and `start_monitoring()` methods exist but are NEVER CALLED.**

### Evidence (from grep search):
```
# Only definitions found, no calls:
backend/app/services/agent_registry.py:298:    async def detect_and_register(
backend/app/services/agent_registry.py:348:    async def start_monitoring(self, interval: int = 10) -> None:
```

### Integration Chain:
1. `agent_detector.py` -> `AgentDetector` class (DETECTED)
2. `agent_registry.py` -> imports `get_agent_detector()` (DETECTED)
3. `agent_registry.py` -> has `detect_and_register()` method (DETECTED, NEVER CALLED)
4. `agent_registry.py` -> has `start_monitoring()` method (DETECTED, NEVER CALLED)
5. `projects.py` -> imports `get_agent_registry()` (DETECTED)
6. `projects.py` -> only calls `get_agents_by_project()` (never triggers detection)

### The Missing Link:
The registry is instantiated in `projects.py` but:
- `detect_and_register()` is never called on startup
- `start_monitoring()` is never called for background health checks
- Agents can only be retrieved if manually registered

### Fix Required:
1. Call `_agent_registry.detect_and_register(project_dir)` when appropriate
2. Call `_agent_registry.start_monitoring()` in FastAPI lifespan
3. Or create a dedicated `/api/agents/detect` endpoint

## Success Criteria

- [ ] Agent detection called at appropriate times
- [ ] Detected agents stored/returned correctly
- [ ] Frontend displays detected agents
- [ ] Detection refreshes on demand or periodically
- [ ] Error handling for detection failures

## Next Steps (After Research)

1. Document exact integration points needed
2. Create implementation plan with code locations
3. Implement integration (startup/API/background)
4. Add frontend integration
5. Test end-to-end agent detection

## Notes

- The detector code is complete and well-designed
- Issue is integration/wiring, not implementation
- Focus research on WHERE to call the detector
- Consider performance implications of process scanning
