# Spec: Quota Alerts

## Objective
Multi-channel alerts at 80%/90%/95% thresholds

## Tasks
1. Create quota_alerts table (id, provider, threshold, triggered_at, acknowledged)
2. Implement alert threshold monitoring
3. Create in-dashboard alert banners
4. Add desktop notifications for alerts
5. Add audio alerts for 95% threshold
6. Create alert history view
7. Implement alert acknowledgment
8. Add alert escalation (repeat if unacknowledged)
9. Create per-provider alert settings
10. Add alert cooldown (prevent spam)

## Acceptance Criteria
- [ ] Alerts trigger at correct thresholds
- [ ] All notification channels work
- [ ] Alert history complete
- [ ] Acknowledgment stops repeat alerts
- [ ] Cooldown prevents spam

## Dependencies
28-auto-pause

## End State
Users notified before quota exhaustion
