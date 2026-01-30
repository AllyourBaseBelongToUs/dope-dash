# Spec: Project Controls

## Objective
Add per-project controls (pause, resume, skip, stop, retry, restart)

## Tasks
1. Create ProjectControls component
2. Implement pause project (all agents)
3. Implement resume project (all agents)
4. Implement skip project (mark as skipped)
5. Implement stop project (terminate all agents)
6. Implement retry project (restart failed specs)
7. Implement restart project (full re-run)
8. Add confirmation modals for destructive actions
9. Create project state machine (idle → running → paused → completed)
10. Add project control history log

## Acceptance Criteria
- [ ] All controls work
- [ ] Agents respond to project controls
- [ ] State transitions valid
- [ ] Confirmation modals prevent accidents
- [ ] Control history shows all actions

## Dependencies
19-portfolio-view

## End State
Projects can be controlled from portfolio view
