# Spec: UI Controls

## Objective
Add pause/resume/skip/stop buttons to dashboard

## Tasks
1. Create ControlButtons component (pause, resume, skip, stop)
2. Implement command sending to Control API
3. Add button loading states during command execution
4. Add visual feedback for command success/failure
5. Disable controls for inactive sessions
6. Add confirmation modal for stop command
7. Create keyboard shortcuts (Space=pause, R=resume, S=skip)
8. Show current agent status badge (running/paused/stopped)
9. Add command history tooltip on hover
10. Handle rapid button clicks with debouncing

## Acceptance Criteria
- [ ] All buttons work and send commands
- [ ] Visual feedback appears within 100ms
- [ ] Stop command requires confirmation
- [ ] Keyboard shortcuts work
- [ ] Buttons disable when agent unavailable

## Dependencies
06-control-api

## End State
Users can control agents from dashboard UI
