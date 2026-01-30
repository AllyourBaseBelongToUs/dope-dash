# Spec: Command Palette

## Objective
Add Ctrl+K command palette with slash commands

## Tasks
1. Create CommandPalette component
2. Implement keyboard shortcut (Ctrl+K, Cmd+K)
3. Create slash command parser (/pause, /resume, /skip, /stop)
4. Add command autocomplete
5. Show command descriptions in palette
6. Add command history (up/down arrows)
7. Implement custom feedback textarea
8. Add smart timeout (30s default, resets on typing)
9. Send custom feedback to agents
10. Create keyboard shortcut for feedback (Ctrl+Enter)

## Acceptance Criteria
- [ ] Ctrl+K opens command palette
- [ ] Slash commands work
- [ ] Autocomplete suggests commands
- [ ] Custom feedback sends to agent
- [ ] Timeout resets on keystroke

## Dependencies
07-ui-controls

## End State
Power users can control agents via keyboard
