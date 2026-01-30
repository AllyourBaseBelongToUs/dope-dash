# Spec: Multi-Agent Unified Model

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
- [ ] All 4 agent types detected
- [ ] Sessions show correct agent type
- [ ] Agent metadata captured automatically
- [ ] Heartbeats detect dead agents
- [ ] Factory creates correct wrappers

## Dependencies
09-error-notifications

## End State
Dashboard shows all agent types uniformly
