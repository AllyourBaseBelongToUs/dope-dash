# Spec: Command History

## Objective
Command sending system with history and replay functionality

## Tasks
1. Create custom command dialog
2. Add command typeahead (previous commands)
3. Create commands_history table
4. Store all sent commands with results
5. Build command history view per project
6. Add command replay button
7. Implement command favorites
8. Create command templates library
9. Add command result filtering
10. Export command history to CSV

## Acceptance Criteria
- [ ] Custom commands send successfully
- [ ] History shows all commands
- [ ] Replay re-sends previous commands
- [ ] Favorites persist across sessions
- [ ] Export includes all context

## Dependencies
21-bulk-operations

## End State
Commands can be sent, tracked, and replayed
