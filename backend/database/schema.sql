-- Dope Dash Database Schema
-- PostgreSQL 16+ with asyncpg driver
--
-- This schema defines the core tables for event storage, session management,
-- spec execution tracking, and time-series metrics.
--
-- Tables:
--   - events: Source of truth for all agent events (30-day retention)
--   - sessions: Session aggregates for overnight runs (1-year retention)
--   - spec_runs: Individual spec execution tracking
--   - metric_buckets: Time-series metrics for performance monitoring
--
-- Retention Policy:
--   - Events: Automatically deleted after 30 days
--   - Sessions: Automatically deleted after 1 year (365 days)
--   - Spec runs and metrics: Cascade deleted with their session

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================================
-- ENUM TYPES
-- ================================================================

CREATE TYPE session_status AS ENUM (
    'running',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE agent_type AS ENUM (
    'ralph',
    'claude',
    'cursor',
    'terminal',
    'crawler',
    'analyzer',
    'reporter',
    'tester',
    'custom'
);

CREATE TYPE spec_run_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'skipped'
);

-- ================================================================
-- TABLES
-- ================================================================

-- Sessions table: aggregates events for overnight runs
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type agent_type NOT NULL,
    project_name TEXT NOT NULL,
    status session_status NOT NULL DEFAULT 'running',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    pid INTEGER,
    working_dir TEXT,
    command TEXT,
    last_heartbeat TIMESTAMPTZ,
    tmux_session TEXT,
    deleted_at TIMESTAMPTZ
);

-- Events table: source of truth for all agent events
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Spec runs table: individual spec execution tracking
CREATE TABLE IF NOT EXISTS spec_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    spec_name TEXT NOT NULL,
    status spec_run_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Metric buckets table: time-series metrics for performance
CREATE TABLE IF NOT EXISTS metric_buckets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    value FLOAT NOT NULL,
    bucket_size INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Deletion log table: tracks all permanent deletions for audit
CREATE TABLE IF NOT EXISTS deletion_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    deletion_type TEXT NOT NULL, -- 'retention', 'manual', 'cascade'
    deleted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_by TEXT, -- 'system', 'user:<user_id>', or 'scheduler'
    metadata JSONB NOT NULL DEFAULT '{}',
    session_id UUID, -- For cascade tracking
    project_name TEXT -- For easier querying
);

-- Commands history table: tracks all custom commands sent to agents
CREATE TYPE command_status AS ENUM (
    'pending',
    'sent',
    'acknowledged',
    'completed',
    'failed',
    'timeout'
);

CREATE TABLE IF NOT EXISTS commands_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    command TEXT NOT NULL,
    status command_status NOT NULL DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    exit_code INTEGER,
    duration_ms INTEGER,
    is_favorite BOOLEAN NOT NULL DEFAULT false,
    template_name VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ================================================================
-- INDEXES
-- ================================================================

-- Sessions indexes
CREATE INDEX IF NOT EXISTS ix_sessions_agent_type ON sessions(agent_type);
CREATE INDEX IF NOT EXISTS ix_sessions_project_name ON sessions(project_name);
CREATE INDEX IF NOT EXISTS ix_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS ix_sessions_project_name_status ON sessions(project_name, status);
CREATE INDEX IF NOT EXISTS ix_sessions_status_started_at ON sessions(status, started_at);
CREATE INDEX IF NOT EXISTS ix_sessions_deleted_at ON sessions(deleted_at);
CREATE INDEX IF NOT EXISTS ix_sessions_pid ON sessions(pid);
CREATE INDEX IF NOT EXISTS ix_sessions_last_heartbeat ON sessions(last_heartbeat);
CREATE INDEX IF NOT EXISTS ix_sessions_tmux_session ON sessions(tmux_session);

-- Events indexes (foreign key + timestamp for common queries)
CREATE INDEX IF NOT EXISTS ix_events_session_id ON events(session_id);
CREATE INDEX IF NOT EXISTS ix_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS ix_events_session_id_created_at ON events(session_id, created_at);
CREATE INDEX IF NOT EXISTS ix_events_event_type_created_at ON events(event_type, created_at);
CREATE INDEX IF NOT EXISTS ix_events_deleted_at ON events(deleted_at);

-- Spec runs indexes
CREATE INDEX IF NOT EXISTS ix_spec_runs_session_id ON spec_runs(session_id);
CREATE INDEX IF NOT EXISTS ix_spec_runs_spec_name ON spec_runs(spec_name);
CREATE INDEX IF NOT EXISTS ix_spec_runs_status ON spec_runs(status);
CREATE INDEX IF NOT EXISTS ix_spec_runs_session_id_spec_name ON spec_runs(session_id, spec_name);
CREATE INDEX IF NOT EXISTS ix_spec_runs_status_started_at ON spec_runs(status, started_at);

-- Metric buckets indexes
CREATE INDEX IF NOT EXISTS ix_metric_buckets_session_id ON metric_buckets(session_id);
CREATE INDEX IF NOT EXISTS ix_metric_buckets_metric_name ON metric_buckets(metric_name);
CREATE INDEX IF NOT EXISTS ix_metric_buckets_timestamp ON metric_buckets(timestamp);
CREATE INDEX IF NOT EXISTS ix_metric_buckets_session_id_timestamp ON metric_buckets(session_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_metric_buckets_metric_name_timestamp ON metric_buckets(metric_name, timestamp);
CREATE INDEX IF NOT EXISTS ix_metric_buckets_session_metric_timestamp ON metric_buckets(session_id, metric_name, timestamp);

-- Deletion log indexes
CREATE INDEX IF NOT EXISTS ix_deletion_log_entity_type ON deletion_log(entity_type);
CREATE INDEX IF NOT EXISTS ix_deletion_log_entity_id ON deletion_log(entity_id);
CREATE INDEX IF NOT EXISTS ix_deletion_log_deleted_at ON deletion_log(deleted_at);
CREATE INDEX IF NOT EXISTS ix_deletion_log_session_id ON deletion_log(session_id);
CREATE INDEX IF NOT EXISTS ix_deletion_log_project_name ON deletion_log(project_name);

-- Commands history indexes
CREATE INDEX IF NOT EXISTS ix_commands_history_project_id ON commands_history(project_id);
CREATE INDEX IF NOT EXISTS ix_commands_history_session_id ON commands_history(session_id);
CREATE INDEX IF NOT EXISTS ix_commands_history_status ON commands_history(status);
CREATE INDEX IF NOT EXISTS ix_commands_history_is_favorite ON commands_history(is_favorite);
CREATE INDEX IF NOT EXISTS ix_commands_history_created_at ON commands_history(created_at);

-- ================================================================
-- FUNCTIONS FOR UPDATED_AT TRIGGER
-- ================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- UPDATED_AT TRIGGERS
-- ================================================================

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_spec_runs_updated_at
    BEFORE UPDATE ON spec_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metric_buckets_updated_at
    BEFORE UPDATE ON metric_buckets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_commands_history_updated_at
    BEFORE UPDATE ON commands_history
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- RETENTION POLICY FUNCTIONS
-- ================================================================

-- Function to delete old events (30-day retention)
CREATE OR REPLACE FUNCTION delete_old_events()
RETURNS void AS $$
BEGIN
    DELETE FROM events
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Function to delete old sessions (1-year retention)
-- This will cascade delete related spec_runs and metric_buckets
CREATE OR REPLACE FUNCTION delete_old_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM sessions
    WHERE created_at < NOW() - INTERVAL '365 days';
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- RETENTION POLICY TRIGGERS
-- ================================================================

-- Trigger to clean up old events after each insert
-- This spreads the deletion load rather than doing it all at once
CREATE OR REPLACE FUNCTION trigger_delete_old_events()
RETURNS TRIGGER AS $$
BEGIN
    -- Only run cleanup occasionally (1 in 100 inserts) to reduce overhead
    -- In production, use pg_cron or a dedicated job instead
    IF (FLOOR(RANDOM() * 100) = 0) THEN
        PERFORM delete_old_events();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_retention_trigger
    AFTER INSERT ON events
    FOR EACH ROW
    EXECUTE FUNCTION trigger_delete_old_events();

-- Trigger to clean up old sessions after each insert
CREATE OR REPLACE FUNCTION trigger_delete_old_sessions()
RETURNS TRIGGER AS $$
BEGIN
    -- Only run cleanup occasionally (1 in 1000 inserts)
    -- Sessions are created less frequently than events
    IF (FLOOR(RANDOM() * 1000) = 0) THEN
        PERFORM delete_old_sessions();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_retention_trigger
    AFTER INSERT ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION trigger_delete_old_sessions();

-- ================================================================
-- COMMENTS
-- ================================================================

COMMENT ON TABLE sessions IS 'Session aggregates for overnight runs (1-year retention)';
COMMENT ON TABLE events IS 'Source of truth for all agent events (30-day retention)';
COMMENT ON TABLE spec_runs IS 'Individual spec execution tracking';
COMMENT ON TABLE metric_buckets IS 'Time-series metrics for performance monitoring';
COMMENT ON TABLE deletion_log IS 'Audit log of all permanent deletions for compliance and debugging';

COMMENT ON COLUMN sessions.metadata IS 'Additional session metadata as JSONB';
COMMENT ON COLUMN sessions.deleted_at IS 'Soft delete timestamp (NULL if not deleted)';
COMMENT ON COLUMN sessions.pid IS 'Agent process ID for multi-agent tracking';
COMMENT ON COLUMN sessions.working_dir IS 'Agent working directory';
COMMENT ON COLUMN sessions.command IS 'Command that started the agent session';
COMMENT ON COLUMN sessions.last_heartbeat IS 'Last heartbeat timestamp for health monitoring';
COMMENT ON COLUMN sessions.tmux_session IS 'Tmux session name for tmux-based agents';

COMMENT ON COLUMN events.data IS 'Event-specific data payload as JSONB';
COMMENT ON COLUMN events.deleted_at IS 'Soft delete timestamp (NULL if not deleted)';

COMMENT ON COLUMN metric_buckets.value IS 'Numeric metric value';
COMMENT ON COLUMN metric_buckets.bucket_size IS 'Time bucket size in seconds';

COMMENT ON COLUMN deletion_log.entity_type IS 'Type of entity deleted (event, session, etc.)';
COMMENT ON COLUMN deletion_log.entity_id IS 'ID of the deleted entity';
COMMENT ON COLUMN deletion_log.deletion_type IS 'Reason for deletion (retention, manual, cascade)';
COMMENT ON COLUMN deletion_log.deleted_by IS 'Who initiated the deletion (system, user, scheduler)';
COMMENT ON COLUMN deletion_log.metadata IS 'Additional deletion context as JSONB';

-- ================================================================
-- SAMPLE QUERIES
-- ================================================================

-- Get all events for a session (ordered by time)
-- SELECT * FROM events WHERE session_id = ? ORDER BY created_at ASC;

-- Get recent events by type
-- SELECT * FROM events WHERE event_type = ? ORDER BY created_at DESC LIMIT 100;

-- Get active sessions
-- SELECT * FROM sessions WHERE status = 'running' ORDER BY started_at DESC;

-- Get session stats
-- SELECT
--     s.id,
--     s.project_name,
--     s.status,
--     COUNT(e.id) as event_count,
--     COUNT(sr.id) as spec_count,
--     COUNT(DISTINCT CASE WHEN sr.status = 'completed' THEN sr.id END) as completed_specs
-- FROM sessions s
-- LEFT JOIN events e ON s.id = e.session_id
-- LEFT JOIN spec_runs sr ON s.id = sr.session_id
-- GROUP BY s.id;

-- Get metrics for a session (time-series)
-- SELECT * FROM metric_buckets
-- WHERE session_id = ? AND metric_name = ?
-- ORDER BY timestamp ASC;
