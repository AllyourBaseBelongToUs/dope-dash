# Spec: Quota Tracking

## Status: 🟡 TODO (Phase 6)

## Objective
Real-time quota tracking per provider (Claude, Gemini, OpenAI, Cursor)

## Tasks
1. Create quota_usage table (provider, current_usage, limit, reset_time)
2. Create providers table (id, name, api_endpoint, rate_limits)
3. Implement quota tracking middleware
4. Add request counter per provider
5. Create quota calculation service
6. Implement quota reset detection
7. Add real-time quota updates via WebSocket
8. Create quota dashboard component
9. Add per-project quota allocation
10. Implement quota overage detection

## Acceptance Criteria
- [ ] All providers tracked
- [ ] Usage updates in real-time
- [ ] Resets detected automatically
- [ ] Dashboard shows current usage
- [ ] Overage alerts trigger

## Implementation Notes
- **Status:** NOT YET IMPLEMENTED - Scheduled for Phase 6
- **Related:** See PHASE-6-RATE-LIMITS.md for details
- **Providers:** Claude, Gemini, OpenAI, Cursor
- **Database:** Requires quota_usage and providers tables

## Dependencies
24-state-machine

## End State
API quota usage tracked in real-time 🟡 TODO
