# Spec: Environment Detection

## Objective
Detect VM vs local environment and adjust behavior

## Tasks
1. Create environment detection utility
2. Detect if running on VM (check hostname, network)
3. Detect if running on local Windows
4. Adjust WebSocket connection URL based on environment
5. Add environment badge to UI
6. Create environment-specific configuration
7. Handle network transition (VM ↔ local)
8. Add fallback to polling if network unavailable
9. Log environment changes
10. Test on both VM and local environments

## Acceptance Criteria
- [ ] Environment detected correctly
- [ ] WebSocket URL adjusts automatically
- [ ] Badge shows current environment
- [ ] Network transitions handled gracefully

## Dependencies
15-notifications

## End State
Dashboard works on VM and local seamlessly
