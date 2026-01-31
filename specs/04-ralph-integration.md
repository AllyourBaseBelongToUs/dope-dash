# Spec: Ralph Integration

## Status: ✅ COMPLETED

## Objective
Integrate with Ralph Inferno agent for event streaming

## Tasks
1. Create Ralph wrapper script backend/wrappers/ralph_wrapper.py
2. Intercept Ralph stdout/stderr for event parsing
3. Emit events: spec_start, spec_complete, error, progress
4. Create Ralph session detection (tmux, process scan)
5. Implement event transformation to JSON format
6. Send events to WebSocket server via HTTP POST
7. Handle Ralph process crashes and restarts
8. Create event schema for Ralph-specific data
9. Test with actual Ralph spec execution
10. Add fallback to polling if WebSocket unavailable

## Acceptance Criteria
- [x] Ralph events captured in real-time
- [x] Events appear in dashboard within 1 second
- [x] Process crashes detected and reported
- [x] Polling fallback works when WebSocket down

## Implementation Notes
- **Event Types:** spec_start, spec_complete, error, progress
- **Session Detection:** tmux session scanning, process detection
- **Polling Fallback:** Automatic when WebSocket unavailable

## Dependencies
03-websocket-server

## End State
Ralph agent telemetry streams to dashboard ✅
