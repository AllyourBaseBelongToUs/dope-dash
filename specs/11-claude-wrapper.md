# Spec: Claude Wrapper

## Status: 🟡 TODO (Phase 3+)

## Objective
Create Claude Code wrapper with stdin/stdout communication

## Tasks
1. Create backend/wrappers/claude_wrapper.py
2. Intercept Claude Code process stdout/stderr
3. Parse Claude-specific events (tool_use, response, error)
4. Implement event transformation to unified schema
5. Send events to WebSocket server
6. Handle Claude session detection
7. Create Claude process lifecycle management
8. Add Claude-specific metadata (model, tools used)
9. Test with actual Claude Code session
10. Add polling fallback for Claude

## Acceptance Criteria
- [ ] Claude events captured in real-time
- [ ] Events appear in dashboard
- [ ] Claude sessions detected automatically
- [ ] Process crashes handled

## Implementation Notes
- **Status:** NOT YET IMPLEMENTED - Scheduled for Phase 3+
- **Dependencies:** Multi-agent unified model (spec 10) needs completion

## Dependencies
10-multi-agent-unified

## End State
Claude Code agent telemetry streams to dashboard 🟡 TODO
