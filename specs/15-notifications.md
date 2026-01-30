# Spec: Notifications

## Objective
Add audio and desktop notifications for important events

## Tasks
1. Create notification service in frontend
2. Implement Web Audio API for sound alerts
3. Create sound toggle button in UI
4. Add notification preferences (all/errors/none)
5. Implement Browser Notification API
6. Request notification permissions on first use
7. Create notification types: spec_complete, error, agent_stopped
8. Add notification history panel
9. Test notification delivery across browsers
10. Create notification settings persistence

## Acceptance Criteria
- [ ] Audio plays on events (when enabled)
- [ ] Desktop notifications appear
- [ ] Toggle persists across sessions
- [ ] Notification preferences work
- [ ] History shows past notifications

## Dependencies
14-analytics-api

## End State
Users receive alerts for important events
