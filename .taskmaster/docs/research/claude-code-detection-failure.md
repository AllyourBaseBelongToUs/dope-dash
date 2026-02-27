# Claude Code Agent Detection Failure - Root Cause Analysis

## Executive Summary

**CRITICAL FINDING: Agent detection is NEVER automatically called.**

The `detect_all_agents()` and `detect_and_register()` methods exist but are **not invoked by any scheduled task, startup hook, or API endpoint**. The detection system is built but completely disconnected from the runtime.

---

## Detailed Code Trace

### 1. Detection Entry Points (Where detection SHOULD be called but ISN'T)

| Component | Status | Evidence |
|-----------|--------|----------|
| Backend `main.py` lifespan | NOT CALLED | No detection call in startup (lines 24-104) |
| Agent Registry singleton | NOT STARTED | `start_monitoring()` never called |
| Agent Pool API | MANUAL ONLY | Only lists DB-registered agents, no detection |
| WebSocket server | NOT INVOLVED | No detection triggers in `websocket.py` |

**File: `vm-code/backend/main.py` (lines 24-104)**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    db_manager.init_db()
    start_scheduler()  # Only for reports
    start_queue_processor()  # For request queue
    # >>> NO AGENT DETECTION INITIALIZATION <<<
    yield
```

### 2. Detection Code (Exists but Unused)

**File: `vm-code/backend/services/agent_detector.py`**

The detection patterns for Claude Code (line 79):
```python
CLAUDE_PATTERNS = ["claude", "claude-code", "anthropic"]
```

Process scanning logic (lines 267-318):
```python
async def _scan_processes(self, project_dir: Path | None = None) -> list[AgentInfo]:
    for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
        # Matches against CLAUDE_PATTERNS
```

**Problem: Windows-specific issues with psutil**
- On Windows, `cmdline` returns a list that may have different structure
- The pattern matching is case-sensitive for command paths
- Claude Code on Windows may have process names like `claude.exe` or node wrappers

### 3. Deduplication Bug

**File: `vm-code/backend/services/agent_detector.py` (lines 118-124)**

```python
# Deduplicate by (agent_type, project_name, pid)
unique_agents: dict[tuple[AgentType, str, int | None], AgentInfo] = {}
for agent in detected:
    key = (agent.agent_type, agent.project_name, agent.pid)
    # Prefer agents with more information (pid > no pid)
    if key not in unique_agents or agent.pid is not None:
        unique_agents[key] = agent
```

**BUG:** When two Claude Code sessions run in the SAME project directory:
- Both have same `agent_type` = CLAUDE
- Both have same `project_name` (extracted from cwd)
- Key becomes `(CLAUDE, "dope-dash", None)` for BOTH
- Only ONE is kept in the dict

### 4. Data Flow Gap

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURRENT BROKEN FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [psutil scan]  ──►  [AgentDetector._scan_processes()]         │
│         │                        │                              │
│         │                        ▼                              │
│         │              [NEVER CALLED]                           │
│         │                        │                              │
│         ▼                        ▼                              │
│  [Agent exists]          [detect_all_agents() unused]          │
│         │                        │                              │
│         │                        ▼                              │
│         │              [detect_and_register() unused]          │
│         │                        │                              │
│         ▼                        ▼                              │
│  [UI shows nothing]      [AgentRegistry empty]                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Frontend Data Source

**File: `vm-code/frontend/store/agentPoolStore.ts`**

The frontend fetches agents from `/api/agent-pool` endpoint (line 164):
```typescript
const response = await service.listAgents({...});
```

This endpoint queries the **database** for registered agents, not the detection system:

**File: `vm-code/backend/api/agent_pool.py` (lines 54-80)**
```python
@router.get("", response_model=dict[str, Any])
async def list_agents(...):
    result = await _pool_service.list_agents(session=session, ...)
    # Queries database, NOT detection
```

### 6. WebSocket Events vs Detection

The main dashboard shows sessions via **WebSocket events**, not detection:

**File: `vm-code/frontend/hooks/useWebSocket.ts`**
- Listens for `session_start` events from agents
- Agents must actively connect and emit events
- Claude Code doesn't emit these events (it's not a Ralph agent)

---

## Root Causes

### Primary Cause: Detection Never Triggered

The `AgentDetector` and `AgentRegistry` services are never initialized or started:
1. `get_agent_detector()` creates singleton but `detect_all_agents()` never called
2. `get_agent_registry()` creates singleton but `start_monitoring()` never called
3. No startup hook, no scheduled task, no API endpoint triggers detection

### Secondary Cause: Windows Process Pattern Issues

Even if detection ran, patterns may not match Claude Code on Windows:
- Claude Code may run as `node.exe` with args
- Process name may be `Code.exe` (VSCode extension)
- cmdline on Windows has different structure

### Tertiary Cause: Deduplication Collapses Multiple Sessions

When multiple sessions have same (type, project, None), only one is kept.

---

## Fix Recommendations

### Fix 1: Add Detection to Startup (CRITICAL)

**File: `vm-code/backend/main.py`**

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ... existing startup code ...

    # Start agent detection and registry monitoring
    try:
        from app.services.agent_registry import get_agent_registry
        registry = get_agent_registry()
        await registry.start_monitoring(interval=10)  # Scan every 10s
        print("Agent detection and monitoring started")
    except Exception as e:
        print(f"Failed to start agent monitoring: {e}")

    yield

    # ... existing shutdown code ...

    # Stop monitoring
    try:
        registry = get_agent_registry()
        await registry.stop_monitoring()
    except Exception:
        pass
```

### Fix 2: Fix Deduplication Key

**File: `vm-code/backend/services/agent_detector.py` (line 119)**

Change from:
```python
key = (agent.agent_type, agent.project_name, agent.pid)
```

To:
```python
# Use PID as primary differentiator, fall back to unique ID for None PIDs
key = (agent.agent_type, agent.project_name, agent.pid or f"no-pid-{id(agent)}")
```

Or better, use working_dir + command:
```python
key = (
    agent.agent_type,
    agent.project_name,
    agent.pid or hash(agent.working_dir + (agent.command or ""))
)
```

### Fix 3: Add Windows-Specific Patterns

**File: `vm-code/backend/services/agent_detector.py` (line 79)**

```python
import platform

if platform.system() == "Windows":
    CLAUDE_PATTERNS = [
        "claude", "claude-code", "anthropic",
        "claude.exe", "Code.exe",  # Windows executables
        "node.exe",  # May run as node process
    ]
else:
    CLAUDE_PATTERNS = ["claude", "claude-code", "anthropic"]
```

### Fix 4: Add Detection API Endpoint

**File: `vm-code/backend/api/agent_pool.py`**

```python
@router.post("/detect", response_model=dict[str, Any])
async def detect_agents(
    project_dir: str | None = Query(None, description="Project directory to scan"),
) -> dict[str, Any]:
    """Trigger agent detection scan."""
    from pathlib import Path
    from app.services.agent_registry import get_agent_registry

    registry = get_agent_registry()

    if project_dir:
        detected = await registry.detect_and_register(project_dir)
    else:
        # Scan all
        from app.services.agent_detector import get_agent_detector
        detector = get_agent_detector()
        detected = await detector.detect_all_agents()

    return {
        "detected": len(detected),
        "agents": [
            {
                "type": a.agent_type.value,
                "project": a.project_name,
                "pid": a.pid,
                "working_dir": a.working_dir,
            }
            for a in detected
        ],
    }
```

### Fix 5: Periodic Background Detection

Add to scheduler or as separate background task:

```python
async def periodic_detection():
    """Background task to periodically detect agents."""
    from app.services.agent_registry import get_agent_registry
    registry = get_agent_registry()

    while True:
        try:
            # Scan common project directories
            # This could be configured or discovered
            detected = await registry.detect_and_register(".")
            logger.debug(f"Periodic detection found {len(detected)} agents")
        except Exception as e:
            logger.error(f"Periodic detection error: {e}")

        await asyncio.sleep(30)  # Every 30 seconds
```

---

## Test Verification

After fixes, verify with:

1. **Check detection is running:**
   ```bash
   curl http://localhost:8000/api/agent-pool/detect
   ```

2. **Check agent registry status:**
   ```bash
   curl http://localhost:8000/api/agent-pool/metrics/health
   ```

3. **Monitor logs for detection:**
   ```bash
   # Should see "Detected N active agents" in logs
   ```

4. **Verify multiple sessions:**
   - Open 2 Claude Code sessions in same project
   - Both should appear in UI after detection runs

---

## Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `vm-code/backend/main.py` | 24-104 | App startup - MISSING detection init |
| `vm-code/backend/services/agent_detector.py` | 71-134, 267-318 | Detection logic |
| `vm-code/backend/services/agent_registry.py` | 298-346, 348-372 | Registration & monitoring |
| `vm-code/backend/api/agent_pool.py` | 54-80 | API endpoint - no detection trigger |
| `vm-code/backend/api/projects.py` | 80-141 | Uses registry but for control only |
| `vm-code/frontend/app/agent-pool/page.tsx` | 44-63 | Frontend - polls API, not detection |
| `vm-code/frontend/store/agentPoolStore.ts` | 158-181 | Store - fetches from API |

---

## Conclusion

The agent detection system is architecturally complete but **functionally dead** - it exists in code but is never executed. The fix requires:

1. **Immediate:** Add `start_monitoring()` call to app startup
2. **Important:** Fix deduplication to support multiple sessions
3. **Enhancement:** Add Windows-specific patterns
4. **Optional:** Add manual detection API endpoint

The 30-second frontend polling (line 58-62 in `agent-pool/page.tsx`) will pick up detected agents once the backend detection is actually running.
