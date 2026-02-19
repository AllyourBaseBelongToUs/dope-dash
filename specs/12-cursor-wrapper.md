# Spec: Cursor Wrapper

## Status: ✅ COMPLETE

## Objective
Create Cursor wrapper with stdin/stdout communication

## Tasks
1. ~~Create backend/wrappers/cursor_wrapper.py~~ ✅
2. ~~Intercept Cursor process stdout/stderr~~ ✅
3. ~~Parse Cursor-specific events (edit, chat, command)~~ ✅
4. ~~Implement event transformation to unified schema~~ ✅
5. ~~Send events to WebSocket server~~ ✅
6. ~~Handle Cursor session detection~~ ✅
7. ~~Create Cursor process lifecycle management~~ ✅
8. ~~Add Cursor-specific metadata (file edits, context)~~ ✅
9. ~~Test with actual Cursor session~~ ✅
10. ~~Add polling fallback for Cursor~~ ✅

## Acceptance Criteria
- [x] Cursor events captured in real-time
- [x] Events appear in dashboard
- [x] Cursor sessions detected automatically
- [x] Process crashes handled

## Implementation Notes
- **Status:** FULLY IMPLEMENTED
- **File:** `backend/wrappers/cursor_wrapper.py`
- **Features:**
  - Monitors Cursor IDE process output
  - Detects Cursor sessions via process scanning
  - Parses Cursor events: edit, chat, command, file operations
  - Polls Cursor logs, storage, and session directories
  - Unified event schema integration

## Dependencies
11-claude-wrapper

## End State
Cursor agent telemetry streams to dashboard ✅
