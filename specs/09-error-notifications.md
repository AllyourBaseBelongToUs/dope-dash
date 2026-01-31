# Spec: Error Notifications

## Status: ✅ COMPLETED

## Objective
Add error detection and query API endpoints

## Tasks
1. Create error detection in event stream
2. Add GET /api/query endpoint for event queries
3. Support filters: session_id, event_type, date_range
4. Create error aggregation by session
5. Add error frequency tracking
6. Create error notification component
7. Show error count badge on sessions
8. Add error detail modal with stack traces
9. Implement error dismissal functionality
10. Create error export to CSV

## Acceptance Criteria
- [x] Errors detected and highlighted
- [x] Query API returns filtered events
- [x] Error badges show current count
- [x] Error modal displays full details
- [x] Export includes all error context

## Implementation Notes
- **Query API:** Part of Core API on port 8000
- **Filters:** session_id, event_type, date_range
- **Export:** CSV format for error analysis

## Dependencies
08-command-palette

## End State
Errors are visible and queryable ✅
