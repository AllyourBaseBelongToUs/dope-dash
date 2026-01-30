# Spec: Retention Policies

## Objective
Implement extended data retention policies

## Tasks
1. Create retention policy service
2. Set event retention to 30 days
3. Set session retention to 1 year
4. Create automated cleanup job
5. Add retention configuration to .env
6. Implement soft delete before permanent deletion
7. Create retention warning notifications
8. Add manual retention extension
9. Log all deletion activity
10. Create retention summary dashboard

## Acceptance Criteria
- [ ] Events deleted after 30 days
- [ ] Sessions deleted after 1 year
- [ ] Cleanup job runs daily
- [ ] Deletions logged
- [ ] Warnings shown before deletion

## Dependencies
17-report-generation

## End State
Data lifecycle managed automatically
