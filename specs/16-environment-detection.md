# Spec: Environment Detection

## Status: ✅ COMPLETED

## Objective
Detect VM vs local environment and adjust behavior

## Tasks
1. Create environment detection utility
2. Detect if running on VM (check hostname, network)
3. Detect if running on local Windows
4. Adjust WebSocket connection URL based on environment
5. Add environment badge to UI
6. Create environment-specific configuration
7. Handle network transition (VM <-> local)
8. Add fallback to polling if network unavailable
9. Log environment changes
10. Test on both VM and local environments

## Acceptance Criteria
- [x] Environment detected correctly
- [x] WebSocket URL adjusts automatically
- [x] Badge shows current environment
- [x] Network transitions handled gracefully

## Implementation Notes
- **VM Detection:** Hostname and network checking
- **WebSocket URL:** Auto-adjusts between localhost (local) and 192.168.206.128 (VM)
- **Environment Badge:** Shows VM or LOCAL in UI
- **Network Fallback:** Automatic polling mode when WebSocket unavailable

## Dependencies
15-notifications

## End State
Dashboard works on VM and local seamlessly ✅
