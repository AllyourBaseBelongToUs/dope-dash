# Spec: Multi-Agent Unified Model

## Status: 🟡 PARTIAL (Ralph implemented, Claude/Cursor/Terminal pending)

## Objective
Create unified session model for Ralph + Claude + Cursor + Terminal

## Tasks
1. Extend sessions table with agent_type enum (ralph, claude, cursor, terminal)
2. Create agent detection service
3. Implement tmux session scanning
4. Implement process scanning for agent binaries
5. Create unified event schema for all agents
6. Add agent metadata to sessions (pid, working_dir, command)
7. Create agent registry pattern
8. Implement agent heartbeat mechanism
9. Add agent capability discovery
10. Create agent factory for wrapper instantiation

## Acceptance Criteria
- [x] Ralph agent type detected
- [ ] Claude agent type detected (TODO)
- [ ] Cursor agent type detected (TODO)
- [ ] Terminal agent type detected (TODO)
- [x] Agent metadata captured automatically (for Ralph)
- [x] Heartbeats detect dead agents
- [x] Factory creates correct wrappers (for Ralph)

## Implementation Notes
- **Completed:** Ralph Inferno integration fully working
- **TODO:** Claude Code wrapper implementation
- **TODO:** Cursor wrapper implementation
- **TODO:** Terminal/tmux wrapper implementation

## Dependencies
09-error-notifications

## End State
Dashboard shows all agent types uniformly (Ralph ✅, others 🟡 TODO)
