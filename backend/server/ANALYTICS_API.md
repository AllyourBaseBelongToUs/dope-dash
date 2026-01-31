# Analytics API Documentation

## Overview

The Analytics API provides on-demand metrics and trends for Dope Dash sessions. It runs on port 8004 and supports session summaries, historical trends, comparison, and export functionality.

**Base URL:** `http://localhost:8004`

## Features

- **Session Summary:** Detailed metrics for individual sessions
- **Historical Trends:** Time-series data over 30/90/365 days
- **Session Comparison:** Side-by-side comparison of multiple sessions
- **On-Demand Rebuild:** Force refresh of cached analytics
- **Export:** Download analytics data as JSON or CSV
- **Caching:** Redis-backed cache with 5-minute TTL

---

## Endpoints

### 1. Root Endpoint

```http
GET /
```

Returns API information and available endpoints.

**Response:**
```json
{
  "name": "Dope Dash Analytics API",
  "version": "0.1.0",
  "status": "running",
  "port": 8004,
  "cache_enabled": true,
  "endpoints": {
    "session_summary": "GET /api/analytics/{session_id}/summary",
    "trends": "GET /api/analytics/trends",
    "compare": "GET /api/analytics/compare",
    "rebuild": "POST /api/analytics/rebuild",
    "export": "GET /api/analytics/export/{format}",
    "health": "/health"
  }
}
```

---

### 2. Health Check

```http
GET /health
```

Check API and database health status.

**Response:**
```json
{
  "status": "healthy",
  "cache_enabled": true,
  "database": "connected"
}
```

---

### 3. Session Summary

```http
GET /api/analytics/{session_id}/summary
```

Get detailed analytics summary for a specific session.

**Path Parameters:**
- `session_id` (string): UUID of the session

**Query Parameters:**
- `use_cache` (boolean, optional): Whether to use cached results (default: `true`)

**Example Request:**
```bash
curl http://localhost:8004/api/analytics/550e8400-e29b-41d4-a716-446655440000/summary
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_type": "ralph",
  "project_name": "dope-dash",
  "status": "completed",
  "total_events": 1250,
  "event_type_counts": {
    "task_start": 50,
    "task_complete": 45,
    "error": 3,
    "warning": 7
  },
  "total_specs": 10,
  "completed_specs": 9,
  "failed_specs": 1,
  "spec_success_rate": 0.9,
  "started_at": "2026-01-30T10:00:00Z",
  "ended_at": "2026-01-30T12:30:00Z",
  "duration_seconds": 9000.0,
  "error_count": 3,
  "warning_count": 7,
  "metric_summary": {
    "cpu_usage": {
      "min": 5.2,
      "max": 89.3,
      "avg": 42.1
    },
    "memory_mb": {
      "min": 512.0,
      "max": 2048.0,
      "avg": 1024.5
    }
  }
}
```

---

### 4. Historical Trends

```http
GET /api/analytics/trends
```

Get historical analytics trends over time.

**Query Parameters:**
- `period` (string): Time period - `30d`, `90d`, or `365d` (default: `30d`)
- `bucket` (string): Time bucket size - `hour`, `day`, `week`, or `month` (default: `day`)
- `use_cache` (boolean): Whether to use cached results (default: `true`)

**Example Request:**
```bash
# Last 30 days, daily buckets
curl "http://localhost:8004/api/analytics/trends?period=30d&bucket=day"

# Last 90 days, weekly buckets
curl "http://localhost:8004/api/analytics/trends?period=90d&bucket=week"

# Last year, monthly buckets
curl "http://localhost:8004/api/analytics/trends?period=365d&bucket=month"
```

**Response:**
```json
{
  "period": "30d",
  "bucket_size": "day",
  "from_date": "2026-01-01T00:00:00Z",
  "to_date": "2026-01-30T23:59:59Z",
  "total_sessions": 45,
  "sessions_by_status": {
    "completed": 38,
    "failed": 5,
    "running": 2
  },
  "sessions_by_agent": {
    "ralph": 25,
    "claude": 12,
    "cursor": 8
  },
  "session_trend": [
    {
      "timestamp": "2026-01-01T00:00:00Z",
      "count": 5
    },
    {
      "timestamp": "2026-01-02T00:00:00Z",
      "count": 3
    }
  ],
  "spec_trend": [
    {
      "timestamp": "2026-01-01T00:00:00Z",
      "total": 25,
      "completed": 23
    }
  ],
  "error_trend": [
    {
      "timestamp": "2026-01-01T00:00:00Z",
      "count": 2
    }
  ],
  "avg_session_duration": 5400.5,
  "total_spec_runs": 450,
  "spec_success_rate": 0.92
}
```

---

### 5. Session Comparison

```http
GET /api/analytics/compare
```

Compare metrics across multiple sessions.

**Query Parameters:**
- `session_ids` (string, required): Comma-separated list of session UUIDs
- `use_cache` (boolean): Whether to use cached results (default: `true`)

**Example Request:**
```bash
curl "http://localhost:8004/api/analytics/compare?session_ids=550e8400-e29b-41d4-a716-446655440000,660e8400-e29b-41d4-a716-446655440001"
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "agent_type": "ralph",
      "project_name": "dope-dash",
      "status": "completed",
      "started_at": "2026-01-30T10:00:00Z",
      "duration_seconds": 9000.0,
      "total_events": 1250,
      "error_count": 3,
      "total_specs": 10,
      "completed_specs": 9,
      "spec_success_rate": 0.9
    },
    {
      "session_id": "660e8400-e29b-41d4-a716-446655440001",
      "agent_type": "claude",
      "project_name": "dope-dash",
      "status": "completed",
      "started_at": "2026-01-30T14:00:00Z",
      "duration_seconds": 7200.0,
      "total_events": 850,
      "error_count": 1,
      "total_specs": 8,
      "completed_specs": 8,
      "spec_success_rate": 1.0
    }
  ],
  "comparison_metrics": {
    "duration": {
      "min": 7200.0,
      "max": 9000.0
    },
    "total_events": {
      "min": 850,
      "max": 1250
    },
    "error_count": {
      "min": 1,
      "max": 3
    },
    "spec_success_rate": {
      "min": 0.9,
      "max": 1.0
    }
  }
}
```

---

### 6. Rebuild Analytics

```http
POST /api/analytics/rebuild
```

Trigger on-demand rebuild of analytics (clears cache).

**Request Body:**
```json
{
  "force": false,
  "session_ids": null
}
```

**Fields:**
- `force` (boolean): Force rebuild even if cache is valid (default: `false`)
- `session_ids` (array of strings, optional): Specific session IDs to rebuild. If `null`, rebuilds all.

**Example Request:**
```bash
# Rebuild all analytics
curl -X POST http://localhost:8004/api/analytics/rebuild \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Rebuild specific sessions
curl -X POST http://localhost:8004/api/analytics/rebuild \
  -H "Content-Type: application/json" \
  -d '{"session_ids": ["550e8400-e29b-41d4-a716-446655440000"]}'
```

**Response:**
```json
{
  "status": "completed",
  "sessions_processed": 45,
  "cache_cleared": 150,
  "started_at": "2026-01-30T12:00:00Z",
  "completed_at": "2026-01-30T12:00:01Z"
}
```

---

### 7. Export Analytics

```http
GET /api/analytics/export/{format}
```

Export analytics data in JSON or CSV format.

**Path Parameters:**
- `format` (string): Export format - `json` or `csv`

**Query Parameters:**
- `session_id` (string, optional): Filter by specific session UUID
- `start_date` (string, optional): Start date in ISO format
- `end_date` (string, optional): End date in ISO format

**Example Requests:**
```bash
# Export all sessions as JSON
curl http://localhost:8004/api/analytics/export/json

# Export specific session as CSV
curl "http://localhost:8004/api/analytics/export/csv?session_id=550e8400-e29b-41d4-a716-446655440000"

# Export date range as JSON
curl "http://localhost:8004/api/analytics/export/json?start_date=2026-01-01T00:00:00Z&end_date=2026-01-30T23:59:59Z"
```

**JSON Response:**
```json
[
  {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_type": "ralph",
    "project_name": "dope-dash",
    "status": "completed",
    "started_at": "2026-01-30T10:00:00Z",
    "ended_at": "2026-01-30T12:30:00Z",
    "metadata": {}
  }
]
```

**CSV Response:**
```csv
Session ID,Agent Type,Project Name,Status,Started At,Ended At,Duration (seconds),PID,Working Dir,Command
550e8400-e29b-41d4-a716-446655440000,ralph,dope-dash,completed,2026-01-30T10:00:00Z,2026-01-30T12:30:00Z,9000.0,12345,/home/user/dope-dash,python main.py
```

---

## Time Bucketing

The trends endpoint supports different time bucket sizes for aggregation:

| Bucket Size | Description | Example Use Case |
|-------------|-------------|------------------|
| `hour` | Hourly buckets | Detailed daily analysis |
| `day` | Daily buckets | Weekly/monthly trends |
| `week` | Weekly buckets | Quarterly analysis |
| `month` | Monthly buckets | Year-over-year comparison |

---

## Caching

The Analytics API uses Redis for caching results with a 5-minute TTL.

**Cache Keys:**
- `analytics:summary:session_id={id}` - Session summary
- `analytics:trends:period={period}:bucket={bucket}` - Trends data
- `analytics:compare:sessions={comma-separated-ids}` - Session comparison

**Cache Invalidation:**
- Automatic expiration after 5 minutes
- Manual rebuild via `/api/analytics/rebuild` endpoint
- Set `use_cache=false` to bypass cache

---

## Running the Server

### Development Mode
```bash
cd backend/server
python analytics.py
```

### Production Mode (with systemd)
```bash
# Start service
systemctl start dope-dash-analytics

# Check status
systemctl status dope-dash-analytics

# View logs
journalctl -u dope-dash-analytics -f
```

### With Docker
```bash
docker run -d \
  --name dope-dash-analytics \
  -p 8004:8004 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/dopedash \
  -e REDIS_URL=redis://redis:6379/0 \
  dope-dash/analytics:latest
```

---

## Error Responses

All endpoints may return standard HTTP error codes:

| Code | Description |
|------|-------------|
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (session doesn't exist) |
| 500 | Internal Server Error |

**Example Error Response:**
```json
{
  "detail": "Session 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

## Dependencies

- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL 15+ with asyncpg driver
- Redis 7+ (optional, for caching)
- uvicorn

---

## Related Specs

- [13-terminal-wrapper](./specs/13-terminal-wrapper.md) - Terminal session tracking
- [12-cursor-wrapper](./specs/12-cursor-wrapper.md) - Cursor IDE integration
- [11-claude-wrapper](./specs/11-claude-wrapper.md) - Claude Code integration
