# Spec: Analytics API

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
- [ ] Summary endpoint returns session metrics
- [ ] Trends endpoint shows historical data
- [ ] Caching improves performance
- [ ] Rebuild trigger refreshes analytics
- [ ] Export formats work

## Dependencies
13-terminal-wrapper

## End State
Historical analytics available via API
