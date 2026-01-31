# Restoration Options Analysis

**Date:** 2026-01-31
**Purpose:** Compare restoration approaches for ralph-monitoring-dashboard
**PostgreSQL Port Analysis:** Included

---

## PostgreSQL Port Investigation

### Current Configuration
- **.env setting:** `localhost:5432`
- **User observation:** Windows uses `5433`
- **VM:** 192.168.206.128

### Analysis

**Why Windows uses 5433:**
- Windows may have multiple PostgreSQL instances
- Common scenario: Native PostgreSQL on 5432, WSL2/Docker instance on 5433
- Port auto-increment when 5432 is already occupied

**VM Situation (192.168.206.128):**
- `.env` is configured for the **VM's backend**, not Windows
- Backend runs on VM, connects to VM's PostgreSQL via `localhost:5432`
- Windows PostgreSQL on port 5433 is **IRRELEVANT** - separate machine

### Port Access Diagram

```
Windows Machine (192.168.206.XX)
    |
    | HTTP/WebSocket
    ↓
VM (192.168.206.128):8000-8004  ← Dashboard accesses these APIs
    |
    | localhost:5432
    ↓
PostgreSQL on VM (local only)    ← Not accessible from Windows (by design)
```

### Recommendation

**NO PORT CHANGE NEEDED**

**Reasoning:**
1. `.env` correctly specifies `localhost:5432` for VM's PostgreSQL
2. Windows PostgreSQL port 5433 is on a different machine
3. Dashboard on Windows calls VM's APIs, not PostgreSQL directly
4. Only the backend (on VM) needs to talk to PostgreSQL

---

## Restoration Options Comparison

### Option A: Add WebSocket Server Only (8001)

**Description:**
- Add WebSocket server on port 8001 for real-time event push
- All other APIs remain in main service (port 8000)
- Control commands go through main API

**Architecture:**
```
┌─────────────────────────────────────┐
│  Dashboard (Frontend)               │
│  Port 8003 (Next.js)                │
└─────────────────────────────────────┘
         ↓              ↓              ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ WebSocket    │  │ Main API     │  │ Analytics    │
│ Port 8001    │  │ Port 8000    │  │ (integrated) │
│ (NEW)        │  │ (existing)   │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Pros:**
- Minimal effort (2-3 days)
- Low complexity
- Fast restoration
- All current APIs remain unchanged
- Easier debugging (single new service)

**Cons:**
- Incomplete vision (40% alignment with SUPER-DUPER-PLAN)
- Tight coupling (WebSocket + Query + Analytics mixed)
- Scalability limits (can't scale WebSocket independently)
- Mixed responsibilities in single service

**Effort:** 2-3 days
- Day 1: WebSocket server implementation
- Day 2: Event broadcasting integration
- Day 3: Dashboard WebSocket client, testing

**Alignment with SUPER-DUPER-PLAN:** 40%

**Migration Risk:** LOW
- No changes to existing APIs
- Incremental deployment possible

---

### Option B: Add WebSocket (8001) + Extract Control API (8002)

**Description:**
- WebSocket server on port 8001 for real-time push
- Separate Control API on port 8002 for agent commands
- Query + Analytics remain in main API (port 8000)

**Architecture:**
```
┌─────────────────────────────────────┐
│  Dashboard (Frontend)               │
│  Port 8003 (Next.js)                │
└─────────────────────────────────────┘
         ↓              ↓              ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ WebSocket    │  │ Control API  │  │ Main API     │
│ Port 8001    │  │ Port 8002    │  │ Port 8000    │
│ (NEW)        │  │ (EXTRACTED)  │  │ (Query +     │
│              │  │              │  │  Analytics)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Pros:**
- Better separation of concerns
- Closer to original vision (70% alignment)
- Independent scaling (WebSocket vs Control)
- Clear responsibilities
- Future-proof architecture

**Cons:**
- Moderate effort (4-5 days)
- More services to manage (2 new services)
- API routing complexity
- Testing overhead for inter-service communication

**Effort:** 4-5 days
- Day 1-2: WebSocket server (8001)
- Day 3-4: Extract Control API from main.py (8002)
- Day 5: Integration testing, dashboard updates

**Alignment with SUPER-DUPER-PLAN:** 70%

**Migration Risk:** MEDIUM
- Need to move Control API endpoints
- Dashboard routing updates required
- Breaking changes if not careful

---

### Option C: Full 4-Service Microservices (8001-8004)

**Description:**
- Port 8001: WebSocket Server (real-time push)
- Port 8002: Control API (agent commands)
- Port 8003: Dashboard (Next.js frontend)
- Port 8004: Analytics API (separate service)

**Architecture:**
```
┌─────────────────────────────────────┐
│  Dashboard (Frontend)               │
│  Port 8003 (Next.js)                │
└─────────────────────────────────────┘
         ↓              ↓              ↓              ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ WebSocket    │  │ Control API  │  │ Query API    │  │ Analytics    │
│ Port 8001    │  │ Port 8002    │  │ Port 8000    │  │ Port 8004    │
│ (NEW)        │  │ (EXTRACTED)  │  │ (main)       │  │ (SEPARATED)  │
│              │  │              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

**Pros:**
- Complete vision alignment (100%)
- Maximum separation of concerns
- Independent scaling for all services
- Best isolation (failure in one doesn't affect others)
- Production-ready microservices
- Team scalability (parallel development)

**Cons:**
- Highest effort (7-10 days)
- High complexity (4 services)
- Overhead (orchestration, health checks, discovery)
- Development overhead (running 4 services locally)
- Deployment complexity
- Network overhead (inter-service latency)

**Effort:** 7-10 days
- Day 1-2: WebSocket Server (8001)
- Day 3-4: Control API (8002)
- Day 5: Analytics API (8004) - already exists, just separate
- Day 6: Dashboard (8003) - already exists, just configure
- Day 7-10: Integration, orchestration, documentation

**Alignment with SUPER-DUPER-PLAN:** 100%

**Migration Risk:** HIGH
- Multiple breaking changes
- Complex inter-service dependencies
- More failure points

---

## Comparison Table

| Criterion | Option A: WebSocket Only | Option B: WS + Control | Option C: Full Microservices |
|-----------|-------------------------|------------------------|------------------------------|
| **Services** | 2 (Main + WebSocket) | 3 (Main + WebSocket + Control) | 4 (Query + WebSocket + Control + Analytics) |
| **Plan Alignment** | 40% | 70% | 100% |
| **Complexity** | Low | Medium | High |
| **Effort** | 2-3 days | 4-5 days | 7-10 days |
| **Migration Risk** | Low | Medium | High |
| **Scalability** | Limited | Good | Excellent |
| **Isolation** | Poor | Good | Excellent |
| **Team Dev** | Limited | Good | Excellent |
| **Debugging** | Easy | Medium | Complex |
| **Deployment** | Simple | Moderate | Complex |
| **Time to Value** | Fast | Medium | Slow |
| **Future-Proof** | Limited | Good | Excellent |

---

## Recommendation

### Primary Recommendation: **Option B (WebSocket + Control API)**

**Why Option B?**

1. **Best balance** of effort vs. vision alignment (70%)
2. **Practical complexity** - manageable without over-engineering
3. **Clear separation** - WebSocket for push, Control for commands, Query for data
4. **Future migration path** - Can evolve to Option C if needed
5. **Reasonable timeline** - 4-5 days is achievable

**Implementation Path:**
```
Phase 1 (Option B - Current goal):
  - Port 8001: WebSocket server (real-time push)
  - Port 8002: Control API (agent commands)
  - Port 8000: Query + Analytics (combined for now)

Phase 2 (Future - evolve to Option C):
  - Port 8004: Extract Analytics to separate service
  - Full microservices when scaling demands it
```

### When to Choose Each Option

**Choose Option A if:**
- Need immediate restoration (< 3 days)
- Team size is 1-2 developers
- Low traffic expected (< 10 concurrent users)
- Quick time-to-value is priority

**Choose Option B if:**
- Have 4-5 days for implementation
- Team size is 2-3 developers
- Medium traffic expected (10-50 concurrent users)
- Want balance of speed and architecture

**Choose Option C if:**
- Have 1-2 weeks for implementation
- Team size is 3+ developers
- High traffic expected (50+ concurrent users)
- Production-ready microservices needed
- Long-term scalability is critical

---

## Current State Assessment

### What Already Exists

**Backend:**
- `backend/app/main.py` - Main FastAPI app with all API routes
- `backend/server/analytics.py` - Analytics API (ready for port 8004)
- `backend/app/api/query.py` - Query endpoints
- `backend/app/api/projects.py` - Project management
- `backend/app/api/commands.py` - Command endpoints
- Database models and migrations in place

**Frontend:**
- `frontend/` - Next.js dashboard (ready for port 8003)

**What's Missing:**
- WebSocket server (port 8001)
- Control API extraction to separate service (port 8002)
- Service orchestration configuration

### Recommended Next Steps

1. **Implement WebSocket Server (8001)**
   - FastAPI + WebSocket support
   - Event broadcasting from existing event store
   - Dashboard WebSocket client integration

2. **Extract Control API (8002)**
   - Move command endpoints from main.py
   - Standalone service with its own database connection
   - Dashboard routing updates

3. **Configure Service Orchestration**
   - Create `docker-compose.yml` or systemd services
   - Health checks for all services
   - Unified startup script

4. **Testing & Validation**
   - Integration testing across services
   - Load testing for WebSocket connections
   - Failover testing

---

## PostgreSQL Configuration Summary

**Current .env is CORRECT. No changes needed.**

```bash
# .env (for VM backend)
DATABASE_URL=postgresql+asyncpg://dopedash:dopedash@localhost:5432/dopedash

# This is correct because:
# - Backend runs on VM (192.168.206.128)
# - Backend connects to VM's PostgreSQL via localhost:5432
# - Windows PostgreSQL on port 5433 is on a different machine (irrelevant)
# - Dashboard on Windows calls VM's APIs, not PostgreSQL directly
```

**Do NOT change to port 5433** - that's Windows-specific, not VM-specific.

---

## Conclusion

**Recommended Approach:** Option B (WebSocket + Control API)
- Effort: 4-5 days
- Plan Alignment: 70%
- Migration Risk: Medium
- Best balance of practicality and vision

**PostgreSQL Port:** No changes needed. Current configuration is correct.
