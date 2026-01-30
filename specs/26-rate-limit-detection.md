# Spec: Rate Limit Detection

## Objective
429 error detection with exponential backoff retry

## Tasks
1. Create rate_limit_events table (id, provider, error_details, retry_after)
2. Implement 429 error detection middleware
3. Parse Retry-After header from responses
4. Create exponential backoff calculator
5. Implement automatic retry queue
6. Add jitter to retry delays (prevent thundering herd)
7. Create max retry limit (5 attempts)
8. Log all rate limit events
9. Add rate limit dashboard view
10. Create rate limit alerts

## Acceptance Criteria
- [ ] 429 errors detected immediately
- [ ] Retry-after headers parsed correctly
- [ ] Backoff exponential (1s, 2s, 4s, 8s, 16s)
- [ ] Jitter prevents synchronized retries
- [ ] Max retries enforced

## Dependencies
25-quota-tracking

## End State
Rate limits handled with auto-retry
