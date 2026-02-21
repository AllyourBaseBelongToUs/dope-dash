# Spec: Multi-Agent Unified Model

## Status: ✅ COMPLETE

## Objective
Create unified session model for Ralph + Claude + Cursor + Terminal

## Tasks
1. ~~Extend sessions table with agent_type enum (ralph, claude, cursor, terminal)~~ ✅
2. ~~Create agent detection service~~ ✅
3. ~~Implement tmux session scanning~~ ✅
4. ~~Implement process scanning for agent binaries~~ ✅
5. ~~Create unified event schema for all agents~~ ✅
6. ~~Add agent metadata to sessions (pid, working_dir, command)~~ ✅
7. ~~Create agent registry pattern~~ ✅
8. ~~Implement agent heartbeat mechanism~~ ✅
9. ~~Add agent capability discovery~~ ✅
10. ~~Create agent factory for wrapper instantiation~~ ✅

## Acceptance Criteria
- [x] Ralph agent type detected
- [x] Claude agent type detected
- [x] Cursor agent type detected
- [x] Terminal agent type detected
- [x] Agent metadata captured automatically (all agents)
- [x] Heartbeats detect dead agents
- [x] Factory creates correct wrappers (all agents)

## Implementation Notes
- **Completed:** All four agent wrappers fully implemented
  - Ralph Inferno integration (`backend/wrappers/ralph_wrapper.py`)
  - Claude Code wrapper (`backend/wrappers/claude_wrapper.py`)
  - Cursor wrapper (`backend/wrappers/cursor_wrapper.py`)
  - Terminal/tmux wrapper (`backend/wrappers/terminal_wrapper.py`)

- **Core Services:**
  - Agent detector: `backend/app/services/agent_detector.py`
  - Agent factory: `backend/app/services/agent_factory.py`
  - Agent registry: `backend/app/services/agent_registry.py`

- **Unified Event Schema:** `backend/app/models/unified_events.py`

- **Migrations:**
  - `002_add_multi_agent_types.py` - Agent types enum
  - `003_add_agent_metadata.py` - Agent metadata fields

## Dependencies
09-error-notifications

## End State
Dashboard shows all agent types uniformly (Ralph ✅, Claude ✅, Cursor ✅, Terminal ✅)
