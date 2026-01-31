# Spec: Terminal Wrapper

## Status: 🟡 TODO (Phase 3+)

## Objective
Create Terminal agent wrapper for shell command tracking

## Tasks
1. Create backend/wrappers/terminal_wrapper.py
2. Track tmux sessions as terminal sessions
3. Parse command execution events
4. Implement event transformation to unified schema
5. Send events to WebSocket server
6. Handle terminal session detection
7. Create command history tracking
8. Add terminal metadata (shell type, working directory)
9. Test with actual terminal sessions
10. Add polling fallback for terminal

## Acceptance Criteria
- [ ] Terminal events captured
- [ ] Commands tracked in dashboard
- [ ] tmux sessions detected
- [ ] Process crashes handled

## Implementation Notes
- **Status:** NOT YET IMPLEMENTED - Scheduled for Phase 3+
- **Dependencies:** Multi-agent unified model (spec 10) needs completion

## Dependencies
12-cursor-wrapper

## End State
Terminal agent telemetry streams to dashboard 🟡 TODO
