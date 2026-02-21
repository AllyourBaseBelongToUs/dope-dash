# Spec: Claude Wrapper

## Status: ✅ COMPLETE

## Objective
Create Claude Code wrapper with stdin/stdout communication

## Tasks
1. ~~Create backend/wrappers/claude_wrapper.py~~ ✅
2. ~~Intercept Claude Code process stdout/stderr~~ ✅
3. ~~Parse Claude-specific events (tool_use, response, error)~~ ✅
4. ~~Implement event transformation to unified schema~~ ✅
5. ~~Send events to WebSocket server~~ ✅
6. ~~Handle Claude session detection~~ ✅
7. ~~Create Claude process lifecycle management~~ ✅
8. ~~Add Claude-specific metadata (model, tools used)~~ ✅
9. ~~Test with actual Claude Code session~~ ✅
10. ~~Add polling fallback for Claude~~ ✅

## Acceptance Criteria
- [x] Claude events captured in real-time
- [x] Events appear in dashboard
- [x] Claude sessions detected automatically
- [x] Process crashes handled

## Implementation Notes
- **Status:** FULLY IMPLEMENTED
- **File:** `backend/wrappers/claude_wrapper.py`
- **Features:**
  - Monitors Claude Code process output
  - Detects Claude sessions via process scanning
  - Parses Claude-specific events: tool_use, response, error, file operations
  - Supports Claude tools: Bash, Read, Write, Edit, Grep, Glob, Task, WebSearch, etc.
  - Unified event schema integration

## Dependencies
10-multi-agent-unified

## End State
Claude Code agent telemetry streams to dashboard ✅
