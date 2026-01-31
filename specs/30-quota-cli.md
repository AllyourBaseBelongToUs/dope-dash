# Spec: Quota CLI Command

## Status: 🟡 TODO (Phase 6)

## Objective
/quota CLI command for terminal users

## Tasks
1. Create quota CLI script in backend/cli/
2. Implement /quota command (show current usage)
3. Add /quota --providers (list all providers)
4. Add /quota --history (show usage over time)
5. Add /quota --reset (show next reset time)
6. Implement colored output (green/yellow/red)
7. Add table formatting for readability
8. Create --json output option
9. Add --watch mode (auto-refresh every 5s)
10. Add help documentation

## Acceptance Criteria
- [ ] /quota displays current usage
- [ ] --providers lists all providers
- [ ] --history shows trends
- [ ] --json works for scripting
- [ ] --watch refreshes automatically

## Implementation Notes
- **Status:** NOT YET IMPLEMENTED - Scheduled for Phase 6
- **Command:** /quota
- **Options:** --providers, --history, --reset, --json, --watch
- **Output:** Colored terminal output (green/yellow/red)

## Dependencies
29-quota-alerts

## End State
Terminal users can check quota via CLI 🟡 TODO
