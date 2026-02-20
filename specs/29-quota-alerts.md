# Spec: Quota Alerts

## Status: ✅ DONE (Phase 6)

## Objective
Multi-channel alerts at 80%/90%/95% thresholds

## Tasks
1. ✅ Create quota_alerts table (id, provider, threshold, triggered_at, acknowledged)
2. ✅ Implement alert threshold monitoring
3. ✅ Create in-dashboard alert banners
4. ✅ Add desktop notifications for alerts
5. ✅ Add audio alerts for 95% threshold
6. ✅ Create alert history view
7. ✅ Implement alert acknowledgment
8. ✅ Add alert escalation (repeat if unacknowledged)
9. ✅ Create per-provider alert settings
10. ✅ Add alert cooldown (prevent spam)

## Acceptance Criteria
- [x] Alerts trigger at correct thresholds
- [x] All notification channels work
- [x] Alert history complete
- [x] Acknowledgment stops repeat alerts
- [x] Cooldown prevents spam

## Implementation Notes
- **Status:** IMPLEMENTED
- **Thresholds:** 80% (warning), 90% (critical), 95% (emergency)
- **Channels:** Dashboard banners, desktop notifications, audio (95%)
- **Database:** quota_alerts table, alert_config table
- **Backend:** QuotaAlertService (app/services/quota_alerts.py)
- **API:** /api/quota/alerts/* endpoints
- **Frontend:** AlertBanner, AlertHistory, AlertConfigPanel components

## Dependencies
28-auto-pause

## End State
Users notified before quota exhaustion ✅ DONE
