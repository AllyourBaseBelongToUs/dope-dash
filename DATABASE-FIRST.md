# Data Persistence Strategy: Database-First Architecture

**Decision:** PostgreSQL as primary storage, not just supplement

---

## User's Insight

> "we defintly want the database tooooo, especially for times where we sleep or are away and the agents do their shenanigans we wnana know exactly what happened"

**Translation:** Database is non-negotiable. We want to know EXACTLY what happened, even when we're asleep.

---

## Architecture

### Storage Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL (VM)                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ events (source of truth)                                 │  │
│  │   - Every event stored with timestamp                   │  │
│  │   - spec_started, spec_completed, spec_failed          │  │
│  │   - intervention_request, timeout_triggered             │  │
│  │   - session_heartbeat, user_feedback                 │  │  │
│  │   - All with full context (JSON metadata)               │  │
│  │                                                            │  │
│  │  sessions (aggregates)                                 │  │
│  │   - Session groups (overnight runs)                     │  │
│  │   - Start/end timestamps, total specs                     │  │  │
│  │   - Final result, cost summary                          │  │
│  │                                                            │  │
│  │  spec_runs (individual executions)                     │  │
│  │   - Per-spec duration, success/failure                  │  │  │
│  │   - Token usage, error details                           │  │
│  │                                                            │  │
│  │  metrics (pre-computed, optional)                     │  │
│  │   - Real-time dashboard numbers                          │  │
│  │   - Hourly/daily aggregates                             │  │
│  └────────────────────────────────────────────────────────┘  │
│                         ↕                                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Dashboard                               │
│  - Queries database for ALL views                               │
│  - WebSocket pushes events (but database is source)             │
│  - No in-memory state (everything from DB)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema (Enhanced)

```sql
-- EVENTS table (source of truth - everything goes here)
CREATE TABLE events (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  event_type VARCHAR(100) NOT NULL,
  data JSONB NOT NULL,              -- Full event context
  session_id UUID,                    -- Link to session
  spec_id TEXT,                       -- Link to spec
  -- Indexes
  INDEX idx_events_type_time (event_type, created_at DESC),
  INDEX idx_events_session (session_id),
  INDEX idx_events_spec (spec_id),
  INDEX idx_events_time (created_at DESC)
);

-- SESSIONS table (aggregates for overnight runs)
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  total_specs INTEGER NOT NULL,
  specs_completed INTEGER DEFAULT 0,
  specs_failed INTEGER DEFAULT 0,
  execution_state TEXT DEFAULT 'running', -- running, completed, failed
  final_result JSONB,
  cost_tokens INTEGER DEFAULT 0,
  cost_usd NUMERIC(10,4),
  metadata JSONB DEFAULT '{}',
  -- Indexes
  INDEX idx_sessions_start (start_time DESC),
  INDEX idx_sessions_state (execution_state)
);

-- SPEC_RUNS table (individual spec executions)
CREATE TABLE spec_runs (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  spec_id TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  duration_seconds INTEGER,
  status TEXT NOT NULL, -- completed, failed, timeout
  tokens_used INTEGER,
  cost_usd NUMERIC(10,4),
  error_message TEXT,
  output_summary JSONB,
  -- Indexes
  INDEX idx_spec_runs_session_spec (session_id, spec_id),
  INDEX idx_spec_runs_time (start_time DESC)
);

-- METRIC_BUCKETS table (optional - for dashboard performance)
CREATE TABLE metric_buckets (
  id BIGSERIAL PRIMARY KEY,
  bucket_time TIMESTAMPTZ NOT NULL,  -- 5-minute buckets
  event_type VARCHAR(100),
  count INTEGER NOT NULL,
  avg_duration_seconds NUMERIC,
  INDEX idx_metrics_time (bucket_time DESC)
);
```

---

## Data Flow

### Event Capture Pipeline

```
Ralph/Claude Agent
    ↓ (does something)
[Event Emitted]
    ↓
[PostgreSQL INSERT]
    ↓
[Persisted to disk]
    ↓
[WebSocket Notification] → Dashboard (if connected)
    ↓
[Database Query] ← Dashboard (polling or on-demand)
```

### Key Principle

**Database writes are IMMEDIATE and PERMANENT.**
- Event occurs → INSERT into events table
- This happens BEFORE WebSocket push
- This happens BEFORE dashboard poll
- Database is source of truth

**Dashboard can always retrieve latest state:**
- WebSocket: Gets pushed events (fast)
- Polling: Queries database (slower but reliable)
- Either way: Same data from database

---

## Retention Policy

### Current MCP Research: 72 hours

**User says:** "we would like more than just 72 hours history if we want"

**New Policy:**

| Data Type | Retention | Rationale |
|-----------|-----------|------------|
| **Events** | 30 days | Debugging recent issues |
| **Sessions** | 1 year | Long-term trend analysis |
| **Spec Runs** | 1 year | Performance tracking |
| **Metric Buckets** | 7 days | Dashboard performance (temporary) |

**Why 1 year for sessions/specs?**
- Long-term trends: "Is performance improving over months?"
- Seasonal patterns: "Do certain specs fail more in winter?"
- Cost tracking: "What's our monthly Claude bill?"

**For longer retention:** Export to external storage (S3, local archives)

---

## Benefits of Database-First Architecture

### 1. No Data Loss (User's Main Requirement)
- Everything stored immediately to PostgreSQL
- Dashboard closed? Data safe in database
- Network disconnected? Data safe in database
- User asleep? Data still being captured

### 2. True History & Analytics
- Query: "What happened last night while I was asleep?"
- Query: "Compare this week's success rate to last week"
- Query: "Which specs fail most often? Show me top 10"
- Query: "What's our total spend on Claude this month?"

### 3. Multiple Clients Support
- Dashboard (Windows browser)
- Mobile app (future)
- CLI tool (`ralph-query status`)
- Claude Code integration
- All read from same source of truth

### 4. Audit & Debugging
- Complete event log for every run
- Reproduce issues by tracing event history
- "Why did CR-02 fail at 3am?" → Check events table
- Build compliance, cost allocation, time tracking

### 5. Backup & Export
- PostgreSQL dump: `pg_dump` for backups
- Export to JSON/CSV for analysis
- Import into other tools (Excel, BI tools)

---

## Memory vs. Database Trade-off

### In-Memory (What we're NOT doing)
```
Pros: Fast, simple, ephemeral
Cons: Lost on crash, no history, no analytics
```

### Database-First (What we ARE doing)
```
Pros: Persistent, queryable, auditable, shareable
Cons: Slightly slower (negligible with indexes), requires setup
```

**Performance Mitigation:**
- BRIN indexes for time-series data (very fast)
- Materialized views for common queries
- Connection pooling (reuse connections)
- Metric buckets for dashboard (pre-computed)

**Verdict:** Database-first is correct choice for "know exactly what happened" requirement.

---

## Implementation Considerations

### Database Setup

```bash
# On VM
sudo -u postgres psql
CREATE DATABASE ralph_monitoring;

\c ralph_monitoring

-- Run schema from above
\i schema.sql

-- Create user for dashboard
CREATE USER ralph_dashboard WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ralph_dashboard;
```

### Connection Management

```python
# monitoring/config.py
from psycopg2.pool import Pool

connection_pool = Pool(
    host='localhost',
    database='ralph_monitoring',
    user='ralph_dashboard',
    password='secure_password',
    minconn=1,
    maxconn=10  # Enough for dashboard + analytics queries
    idle_timeout_ms=30000  # Close idle connections after 30s
)
```

### Event Storage

```python
# monitoring/event_store.py
async def store_event(event_type: str, data: dict, session_id: str = None):
    """Store event to database (source of truth)"""
    async with connection_pool.connection() as conn:
        await conn.execute(
            """INSERT INTO events (event_type, data, session_id)
             VALUES ($1, $2, $3)""",
            (event_type, json.dumps(data), session_id)
        )

        # Immediate write, no buffering
        await conn.commit()

    # Then push to WebSocket (non-blocking)
    await broadcast_to_websocket(event_type, data)
```

---

## Cost Estimation

### Storage Requirements

| Entity | Size per Record | Records/Day | 30 Days |
|---------|-----------------|-------------|---------|
| Events | ~1 KB | ~5,000 | ~150 MB |
| Sessions | ~2 KB | ~10 | ~600 KB |
| Spec Runs | ~3 KB | ~50 | ~4.5 MB |

**Total 30-day storage:** ~155 MB (negligible)

**PostgreSQL can easily handle:** Terabytes (years of data)

### Performance

| Query | Time (with indexes) |
|-------|----------------------|
| Get last 100 events | <10ms |
| Get session summary | <20ms |
| Compare two sessions | <50ms |
| Get metrics for dashboard | <5ms |

---

## Migration from In-Memory

### Old (In-Memory Only)
```typescript
// Session in RAM, lost on crash
class SessionManager {
  private currentSession: Session;  // Lost if process crashes!

  saveSession() {
    // Optional persistence to JSON file
  }
}
```

### New (Database-First)
```typescript
// Session in database, survives anything
class SessionManager {
  private sessionId: UUID;

  async saveEvent(event: Event) {
    // IMMEDIATE database write
    await db.events.insert(event);
  }

  async getSession(sessionId: UUID): Promise<Session> {
    // Load from database
    return await db.sessions.findOne({ where: { id: sessionId } });
  }

  async getHistory(): Promise<Session[]> {
    // Query database for all sessions
    return await db.sessions.find().orderBy('startTime', 'desc').limit(100);
  }
}
```

---

## Summary

**Answer to user:** Database is non-negotiable. We're doing database-first.

**Key points:**
- PostgreSQL as source of truth (everything stored immediately)
- Events captured 24/7, even while sleeping
- WebSocket for real-time (push notifications), polling for on-demand
- Retention: 30 days for events, 1 year for sessions/specs
- No progress lost regardless of connection state
- Query database to know "exactly what happened"

**Why this matters:** You can wake up, check database, and see EVERYTHING that happened overnight. No ambiguity, no "connection was lost so we don't know", no gaps. Complete audit trail.

---

## Success Criteria

✅ PostgreSQL as primary storage
✅ All events stored immediately
✅ Dashboard queries database (not in-memory)
✅ WebSocket for push (optimization, not requirement)
✅ Polling for fallback (reliability, not optimization)
✅ Extended retention (30 days events, 1 year sessions)
✅ No data loss possible (database persists everything)
