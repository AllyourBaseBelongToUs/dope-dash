# Spec: Auto-Pause

## Status: ✅ COMPLETE

## Objective
Auto-pause at 95% quota (lowest priority projects first)

## Tasks
1. ✅ Create project priority field (high, medium, low) - Already exists in Project model
2. ✅ Implement quota threshold monitoring (80%, 90%, 95%)
3. ✅ Create auto-pause trigger service
4. ✅ Implement priority-based pause order
5. ✅ Add pre-pause warning (10% buffer)
6. ✅ Create auto-resume after quota reset
7. ✅ Add manual override for auto-pause
8. ✅ Create auto-pause history log
9. ✅ Add auto-pause notification
10. ✅ Create auto-pause settings per project

## Acceptance Criteria
- [x] Projects pause at 95% quota
- [x] Low priority projects pause first
- [x] Warnings sent before pause
- [x] Auto-resume works after reset
- [x] Manual override available

## Implementation Notes
- **Status:** IMPLEMENTED
- **Thresholds:** 80% (warning), 95% (auto-pause) - configurable per project
- **Priority Order:** Low -> Medium -> High -> Critical
- **Buffer:** 10% warning before auto-pause

## Files Created/Modified
- `backend/app/models/auto_pause.py` - AutoPauseLog model and schemas
- `backend/app/services/auto_pause.py` - AutoPauseService with core logic
- `backend/app/api/auto_pause.py` - API endpoints
- `backend/app/services/notifications.py` - Added auto-pause notification types
- `backend/app/main.py` - Registered auto-pause router
- `frontend/src/types/index.ts` - TypeScript types for auto-pause
- `frontend/src/components/portfolio/ProjectCard.tsx` - Auto-paused indicator

## API Endpoints
- `GET /api/auto-pause/projects/{id}/settings` - Get auto-pause settings
- `PATCH /api/auto-pause/projects/{id}/settings` - Update settings
- `GET /api/auto-pause/projects/{id}/status` - Get status
- `POST /api/auto-pause/projects/{id}/override` - Manual override
- `GET /api/auto-pause/projects/{id}/history` - Pause history
- `GET /api/auto-pause/history` - All pause history
- `POST /api/auto-pause/check` - Trigger quota check
- `POST /api/auto-pause/check-resume` - Trigger resume check

## Dependencies
27-request-queue (COMPLETE)

## End State
Projects auto-pause to prevent quota exhaustion ✅ COMPLETE
