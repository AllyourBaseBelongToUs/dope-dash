# Spec: Dashboard MVP

## Status: ✅ COMPLETED

## Objective
Create Next.js dashboard with real-time progress display

## Tasks
1. Initialize Next.js app in frontend/ with TypeScript
2. Create Tailwind CSS configuration
3. Create WebSocket client hook (useWebSocket)
4. Create polling client hook (usePolling) as fallback
5. Create session state management (Zustand)
6. Build main page: / (dashboard view)
7. Display spec progress: "3 of 11 specs complete"
8. Display current spec: "Currently running: CR-02"
9. Show active sessions list
10. Add auto-reconnect on WebSocket disconnect

## Acceptance Criteria
- [x] Dashboard accessible on port 8003
- [x] Real-time updates from WebSocket
- [x] Polling fallback works when WebSocket unavailable
- [x] Progress displays correctly
- [x] Page refreshes maintain state

## Implementation Notes
- **Framework:** Next.js 15 + React 19 + TypeScript
- **Service Startup:** `cd frontend && npm run dev` (port 8003)
- **WebSocket:** Auto-retry every 3 minutes, manual retry button in polling mode
- **Virtualization:** react-virtuoso for efficient event list rendering
- **State Management:** Zustand for global state
- **Settings Page:** Export/import, search, preview mode
- **Environment Detection:** VM vs local detection with URL adjustment
- **Notifications:** Sound toggle, desktop toggle, preference levels
- **Command Palette:** Keyboard shortcuts (Ctrl+K)
- **NO DOCKER:** Direct Next.js dev server startup

## Dependencies
04-ralph-integration

## End State
Basic dashboard shows Ralph agent progress in real-time ✅
