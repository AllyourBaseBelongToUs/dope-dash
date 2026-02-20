# Spec: Quota Tracking

## Status: ✅ COMPLETE

## Objective
Real-time quota tracking per provider (Claude, Gemini, OpenAI, Cursor)

## Tasks
1. ✅ Create quota_usage table (provider, current_usage, limit, reset_time)
2. ✅ Create providers table (id, name, api_endpoint, rate_limits)
3. ✅ Implement quota tracking middleware
4. ✅ Add request counter per provider
5. ✅ Create quota calculation service
6. ✅ Implement quota reset detection
7. ✅ Add real-time quota updates via WebSocket
8. ✅ Create quota dashboard component
9. ✅ Add per-project quota allocation
10. ✅ Implement quota overage detection

## Acceptance Criteria
- [x] All providers tracked
- [x] Usage updates in real-time
- [x] Resets detected automatically
- [x] Dashboard shows current usage
- [x] Overage alerts trigger

## Implementation Notes
- **Status:** COMPLETE
- **Backend:** `backend/app/services/quota.py` - QuotaService with CRUD, reset detection, alerts
- **API:** `backend/app/api/quota.py` - REST endpoints for providers, usage, alerts, summary
- **Models:** `backend/app/models/quota.py` - Provider, QuotaUsage, QuotaAlert models
- **Frontend:** `frontend/src/components/quota/QuotaDashboard.tsx` - Dashboard component
- **Database:** Migration 010_add_quota_tracking_tables.py
- **Providers:** Claude, Gemini, OpenAI, Cursor (seeded in migration)

## Dependencies
24-state-machine

## End State
API quota usage tracked in real-time ✅ DONE
