# Spec: Project Controls

## Status: ✅ COMPLETED

## Objective
Add per-project controls (pause, resume, skip, stop, retry, restart)

## Tasks
1. Create ProjectControls component ✅
2. Implement pause project (all agents) ✅
3. Implement resume project (all agents) ✅
4. Implement skip project (mark as skipped) ✅
5. Implement stop project (terminate all agents) ✅
6. Implement retry project (restart failed specs) ✅
7. Implement restart project (full re-run) ✅
8. Add confirmation modals for destructive actions ✅
9. Create project state machine (idle -> running -> paused -> completed) ✅
10. Add project control history log ✅

## Acceptance Criteria
- [x] All controls work
- [x] Agents respond to project controls
- [x] State transitions valid
- [x] Confirmation modals prevent accidents
- [x] Control history shows all actions

## Implementation Notes
- **Status:** COMPLETED
- **Commands:** pause, resume, skip, stop, retry, restart
- **State Machine:** idle -> running -> paused -> completed
- **Signal Handling:** SIGTERM (stop), SIGUSR1 (pause), SIGUSR2 (resume)

## Dependencies
19-portfolio-view

## End State
Projects can be controlled from portfolio view ✅ DONE
