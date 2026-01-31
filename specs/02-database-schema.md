# Spec: Database Schema

## Status: ✅ COMPLETED

## Objective
Create PostgreSQL database schema with events, sessions, spec_runs, metric_buckets tables

## Tasks
1. Create backend/database/schema.sql with all tables
2. Create events table: id, session_id, event_type, data, created_at
3. Create sessions table: id, agent_type, project_name, status, metadata, started_at, ended_at
4. Create spec_runs table: id, session_id, spec_name, status, started_at, completed_at
5. Create metric_buckets table: id, session_id, metric_name, value, bucket_size, timestamp
6. Create indexes on foreign keys and timestamp columns
7. Create database migration system (alembic)
8. Create initial migration 001_initial_schema.sql
9. Add retention policy triggers (30 days events, 1 year sessions)
10. Create database connection pool in backend/db/connection.py

## Acceptance Criteria
- [x] All tables created with proper constraints
- [x] Indexes improve query performance
- [x] Migration system works forward and backward
- [x] Connection pool handles 20+ concurrent connections (15 pool + 5 overflow per service)
- [x] Retention policies enforce data lifecycle

## Implementation Notes
- **Connection Pooling:** 15 base connections + 5 overflow per service (5 services = 100 total max)
- **Port:** PostgreSQL on localhost:5432
- **Retention:** 30 days for events, 1 year for sessions
- **Migration System:** Alembic-based for version control
- **First-Party:** Database is the source of truth, not a cache

## Dependencies
01-project-setup

## End State
PostgreSQL database ready for event storage ✅
