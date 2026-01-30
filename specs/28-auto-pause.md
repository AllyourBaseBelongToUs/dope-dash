# Spec: Auto-Pause

## Objective
Auto-pause at 95% quota (lowest priority projects first)

## Tasks
1. Create project priority field (high, medium, low)
2. Implement quota threshold monitoring (80%, 90%, 95%)
3. Create auto-pause trigger service
4. Implement priority-based pause order
5. Add pre-pause warning (10% buffer)
6. Create auto-resume after quota reset
7. Add manual override for auto-pause
8. Create auto-pause history log
9. Add auto-pause notification
10. Create auto-pause settings per project

## Acceptance Criteria
- [ ] Projects pause at 95% quota
- [ ] Low priority projects pause first
- [ ] Warnings sent before pause
- [ ] Auto-resume works after reset
- [ ] Manual override available

## Dependencies
27-request-queue

## End State
Projects auto-pause to prevent quota exhaustion
