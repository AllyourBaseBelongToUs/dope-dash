# Spec: Terminal Wrapper

## Status: ✅ COMPLETE

## Objective
Create Terminal agent wrapper for shell command tracking

## Tasks
1. ~~Create backend/wrappers/terminal_wrapper.py~~ ✅
2. ~~Track tmux sessions as terminal sessions~~ ✅
3. ~~Parse command execution events~~ ✅
4. ~~Implement event transformation to unified schema~~ ✅
5. ~~Send events to WebSocket server~~ ✅
6. ~~Handle terminal session detection~~ ✅
7. ~~Create command history tracking~~ ✅
8. ~~Add terminal metadata (shell type, working directory)~~ ✅
9. ~~Test with actual terminal sessions~~ ✅
10. ~~Add polling fallback for terminal~~ ✅

## Acceptance Criteria
- [x] Terminal events captured
- [x] Commands tracked in dashboard
- [x] tmux sessions detected
- [x] Process crashes handled

## Implementation Notes
- **Status:** FULLY IMPLEMENTED
- **File:** `backend/wrappers/terminal_wrapper.py`
- **Features:**
  - Tracks tmux sessions as terminal sessions
  - Monitors shell history files (.bash_history, .zsh_history, .fish_history)
  - Parses command execution events
  - Supports multiple shell types (bash, zsh, fish, sh)
  - Unified event schema integration

## Dependencies
12-cursor-wrapper

## End State
Terminal agent telemetry streams to dashboard ✅
