# Atom 2: Port Architecture Design

**AOT Session:** 2026-01-23
**Execution:** Direct (not delegated)
**Complexity:** Simple
**Reasoning:** User specifically noted port conflicts with localhost:3000

---

## Task Description

Design port allocation scheme avoiding dev server conflicts with explicit IP bindings.

**User's Concern:** "the ports might be conflicts cause they are super close to test ports like localhost 3000, what do you say would be better having some explicit 192.168 etc Addresses for the dashboard and its servers?"

---

## Independence Analysis

This atom is **independent** because:
- Standalone architectural decision
- No dependencies on other atoms
- Can be changed without affecting other components

---

## Execution

**Handled directly** (no delegation needed)

---

## Result

### Port Allocation Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     VM (192.168.206.128) - Port Map                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DEV SERVERS (Project-specific, localhost binding)                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 3000: nonprofit-matcher (localhost only)                         │    │
│  │ 3001: project-alpha (localhost only)                             │    │
│  │ 3002: project-beta (localhost only)                              │    │
│  │ 3003-3099: Available for more projects                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  MONITORING INFRASTRUCTURE (Explicit IP, different range)               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 8001: Ralph Monitoring WebSocket (0.0.0.0 - all interfaces)     │    │
│  │ 8002: Ralph Query API (0.0.0.0)                                  │    │
│  │ 8003: Dashboard Frontend (0.0.0.0)                               │    │
│  │ 8004: PostgreSQL (localhost only, internal)                       │    │
│  │ 8005-8099: Available for future services                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ACCESS FROM WINDOWS:                                                   │
│  - Dev servers: Via SSH tunnel (localhost:3000 → VM:localhost:3000)    │
│  - Monitoring: Direct to 192.168.206.128:8001-8003                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why This Works

**Dev Servers (3000-3099 range):**
- Bind to `127.0.0.1` (localhost only)
- Not accessible from Windows without SSH tunnel
- Prevents accidental external access

**Monitoring Infrastructure (8000-8099 range):**
- Bind to `0.0.0.0` (all interfaces)
- Accessible from Windows: `http://192.168.206.128:8003`
- Different range eliminates conflicts

### Configuration Examples

**Project 1: nonprofit-matcher**
```bash
# Dev server (localhost only)
PORT=3000 HOST=127.0.0.1 npm run dev
# Access from Windows: localhost:3000 (via SSH tunnel)
```

**Project 2: project-alpha**
```bash
# Dev server (localhost only)
PORT=3001 HOST=127.0.0.1 npm run dev
# Access from Windows: localhost:3001 (via SSH tunnel)
```

**Monitoring Infrastructure**
```bash
# WebSocket server (all interfaces)
RALPH_WS_PORT=8001 RALPH_WS_HOST=0.0.0.0 python monitoring/websocket_server.py

# Query API (all interfaces)
RALPH_API_PORT=8002 RALPH_API_HOST=0.0.0.0 node monitoring/api.js

# Dashboard (all interfaces)
DASHBOARD_PORT=8003 HOST=0.0.0.0 npm run dev
# Access from Windows: http://192.168.206.128:8003
```

### Environment Variables

```bash
# ~/.bashrc on VM
export RALPH_MONITORING_WS_PORT=8001
export RALPH_MONITORING_WS_HOST=0.0.0.0
export RALPH_MONITORING_API_PORT=8002
export RALPH_MONITORING_DASHBOARD_PORT=8003
export POSTGRES_PORT=5432
export POSTGRES_HOST=localhost
```

---

## Success Criteria

✅ Port conflicts eliminated (different ranges)
✅ Explicit IP bindings defined (0.0.0.0 vs 127.0.0.1)
✅ Access from Windows clarified (direct vs SSH tunnel)
✅ Dev servers protected (localhost only)
✅ Configuration examples provided

---

## Key Decision

**User's question answered:**
- Yes, use explicit IP addresses: `0.0.0.0` for monitoring services
- Different port range: 8000s instead of 3000s
- Clear separation: Dev (localhost) vs Monitoring (all interfaces)
