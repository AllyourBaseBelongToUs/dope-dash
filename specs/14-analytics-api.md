# Spec: Analytics API

## Status: ✅ COMPLETED

## Objective
Create analytics API for on-demand metrics and trends

## Tasks
1. Create backend/server/analytics.py (FastAPI, port 8004)
2. Implement GET /api/analytics/:session_id/summary
3. Implement GET /api/analytics/trends (30/90/365 days)
4. Create metric aggregation queries
5. Implement time bucketing (hour, day, week, month)
6. Add on-demand analytics rebuild trigger
7. Cache analytics results (5-minute TTL)
8. Support comparison between sessions
9. Export analytics to JSON/CSV
10. Document API with examples

## Acceptance Criteria
- [x] Summary endpoint returns session metrics
- [x] Trends endpoint shows historical data
- [x] Caching improves performance
- [x] Rebuild trigger refreshes analytics
- [x] Export formats work

## Implementation Notes
- **Service Startup:** `uvicorn backend.server.analytics:app --host 0.0.0.0 --port 8004`
- **Caching:** Redis cache with 5-minute TTL
- **Time Buckets:** hour, day, week, month
- **Export Formats:** JSON, CSV
- **NO DOCKER:** Direct uvicorn service startup

## Dependencies
13-terminal-wrapper

## End State
Historical analytics available via API ✅
