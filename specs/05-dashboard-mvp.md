# Spec: Dashboard MVP

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
- [ ] Dashboard accessible on port 8003
- [ ] Real-time updates from WebSocket
- [ ] Polling fallback works when WebSocket unavailable
- [ ] Progress displays correctly
- [ ] Page refreshes maintain state

## Dependencies
04-ralph-integration

## End State
Basic dashboard shows Ralph agent progress in real-time
