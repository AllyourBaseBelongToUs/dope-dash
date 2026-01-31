"""Initial schema: events, sessions, spec_runs, metric_buckets tables.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-30

This migration creates the core database schema for Dope Dash:
- sessions: Agent session tracking
- events: Agent event storage
- spec_runs: Spec execution tracking
- metric_buckets: Time-series metrics

Includes retention policy triggers:
- Events: 30-day retention
- Sessions: 1-year retention
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
import enum


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to create all tables, indexes, and triggers."""
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create ENUM types
    session_status_enum = sa.ENUM(
        'running', 'completed', 'failed', 'cancelled',
        name='session_status',
        create_type=True,
    )
    session_status_enum.create(op.get_bind(), checkfirst=True)

    agent_type_enum = sa.ENUM(
        'crawler', 'analyzer', 'reporter', 'tester', 'custom',
        name='agent_type',
        create_type=True,
    )
    agent_type_enum.create(op.get_bind(), checkfirst=True)

    spec_run_status_enum = sa.ENUM(
        'pending', 'running', 'completed', 'failed', 'skipped',
        name='spec_run_status',
        create_type=True,
    )
    spec_run_status_enum.create(op.get_bind(), checkfirst=True)

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('agent_type', agent_type_enum, nullable=False),
        sa.Column('project_name', sa.Text(), nullable=False),
        sa.Column('status', session_status_enum, nullable=False, server_default='running'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_events_session_id_sessions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create spec_runs table
    op.create_table(
        'spec_runs',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('spec_name', sa.Text(), nullable=False),
        sa.Column('status', spec_run_status_enum, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_spec_runs_session_id_sessions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create metric_buckets table
    op.create_table(
        'metric_buckets',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('bucket_size', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_metric_buckets_session_id_sessions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for sessions
    op.create_index('ix_sessions_agent_type', 'sessions', ['agent_type'])
    op.create_index('ix_sessions_project_name', 'sessions', ['project_name'])
    op.create_index('ix_sessions_status', 'sessions', ['status'])
    op.create_index('ix_sessions_project_name_status', 'sessions', ['project_name', 'status'])
    op.create_index('ix_sessions_status_started_at', 'sessions', ['status', 'started_at'])

    # Create indexes for events
    op.create_index('ix_events_session_id', 'events', ['session_id'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_session_id_created_at', 'events', ['session_id', 'created_at'])
    op.create_index('ix_events_event_type_created_at', 'events', ['event_type', 'created_at'])

    # Create indexes for spec_runs
    op.create_index('ix_spec_runs_session_id', 'spec_runs', ['session_id'])
    op.create_index('ix_spec_runs_spec_name', 'spec_runs', ['spec_name'])
    op.create_index('ix_spec_runs_status', 'spec_runs', ['status'])
    op.create_index('ix_spec_runs_session_id_spec_name', 'spec_runs', ['session_id', 'spec_name'])
    op.create_index('ix_spec_runs_status_started_at', 'spec_runs', ['status', 'started_at'])

    # Create indexes for metric_buckets
    op.create_index('ix_metric_buckets_session_id', 'metric_buckets', ['session_id'])
    op.create_index('ix_metric_buckets_metric_name', 'metric_buckets', ['metric_name'])
    op.create_index('ix_metric_buckets_timestamp', 'metric_buckets', ['timestamp'])
    op.create_index('ix_metric_buckets_session_id_timestamp', 'metric_buckets', ['session_id', 'timestamp'])
    op.create_index('ix_metric_buckets_metric_name_timestamp', 'metric_buckets', ['metric_name', 'timestamp'])
    op.create_index('ix_metric_buckets_session_metric_timestamp', 'metric_buckets', ['session_id', 'metric_name', 'timestamp'])

    # Create updated_at trigger function
    op.execute('''
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Create updated_at triggers for each table
    op.execute('''
        CREATE TRIGGER update_sessions_updated_at
        BEFORE UPDATE ON sessions
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    op.execute('''
        CREATE TRIGGER update_events_updated_at
        BEFORE UPDATE ON events
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    op.execute('''
        CREATE TRIGGER update_spec_runs_updated_at
        BEFORE UPDATE ON spec_runs
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    op.execute('''
        CREATE TRIGGER update_metric_buckets_updated_at
        BEFORE UPDATE ON metric_buckets
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    # Create retention policy functions
    # Delete old events (30-day retention)
    op.execute('''
        CREATE OR REPLACE FUNCTION delete_old_events()
        RETURNS void AS $$
        BEGIN
            DELETE FROM events
            WHERE created_at < NOW() - INTERVAL '30 days';
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Delete old sessions (1-year retention) - cascades to spec_runs and metric_buckets
    op.execute('''
        CREATE OR REPLACE FUNCTION delete_old_sessions()
        RETURNS void AS $$
        BEGIN
            DELETE FROM sessions
            WHERE created_at < NOW() - INTERVAL '365 days';
        END;
        $$ LANGUAGE plpgsql;
    ''')

    # Create retention policy triggers (probabilistic to spread load)
    op.execute('''
        CREATE OR REPLACE FUNCTION trigger_delete_old_events()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (FLOOR(RANDOM() * 100) = 0) THEN
                PERFORM delete_old_events();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    op.execute('''
        CREATE TRIGGER events_retention_trigger
        AFTER INSERT ON events
        FOR EACH ROW
        EXECUTE FUNCTION trigger_delete_old_events();
    ''')

    op.execute('''
        CREATE OR REPLACE FUNCTION trigger_delete_old_sessions()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (FLOOR(RANDOM() * 1000) = 0) THEN
                PERFORM delete_old_sessions();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    op.execute('''
        CREATE TRIGGER sessions_retention_trigger
        AFTER INSERT ON sessions
        FOR EACH ROW
        EXECUTE FUNCTION trigger_delete_old_sessions();
    ''')


def downgrade() -> None:
    """Downgrade to remove all tables, indexes, and triggers."""
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS sessions_retention_trigger ON sessions')
    op.execute('DROP TRIGGER IF EXISTS events_retention_trigger ON events')
    op.execute('DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions')
    op.execute('DROP TRIGGER IF EXISTS update_events_updated_at ON events')
    op.execute('DROP TRIGGER IF EXISTS update_spec_runs_updated_at ON spec_runs')
    op.execute('DROP TRIGGER IF EXISTS update_metric_buckets_updated_at ON metric_buckets')

    # Drop functions
    op.execute('DROP FUNCTION IF EXISTS trigger_delete_old_sessions()')
    op.execute('DROP FUNCTION IF EXISTS trigger_delete_old_events()')
    op.execute('DROP FUNCTION IF EXISTS delete_old_sessions()')
    op.execute('DROP FUNCTION IF EXISTS delete_old_events()')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')

    # Drop indexes (in reverse order)
    op.drop_index('ix_metric_buckets_session_metric_timestamp', table_name='metric_buckets')
    op.drop_index('ix_metric_buckets_metric_name_timestamp', table_name='metric_buckets')
    op.drop_index('ix_metric_buckets_session_id_timestamp', table_name='metric_buckets')
    op.drop_index('ix_metric_buckets_timestamp', table_name='metric_buckets')
    op.drop_index('ix_metric_buckets_metric_name', table_name='metric_buckets')
    op.drop_index('ix_metric_buckets_session_id', table_name='metric_buckets')

    op.drop_index('ix_spec_runs_status_started_at', table_name='spec_runs')
    op.drop_index('ix_spec_runs_session_id_spec_name', table_name='spec_runs')
    op.drop_index('ix_spec_runs_status', table_name='spec_runs')
    op.drop_index('ix_spec_runs_spec_name', table_name='spec_runs')
    op.drop_index('ix_spec_runs_session_id', table_name='spec_runs')

    op.drop_index('ix_events_event_type_created_at', table_name='events')
    op.drop_index('ix_events_session_id_created_at', table_name='events')
    op.drop_index('ix_events_event_type', table_name='events')
    op.drop_index('ix_events_session_id', table_name='events')

    op.drop_index('ix_sessions_status_started_at', table_name='sessions')
    op.drop_index('ix_sessions_project_name_status', table_name='sessions')
    op.drop_index('ix_sessions_status', table_name='sessions')
    op.drop_index('ix_sessions_project_name', table_name='sessions')
    op.drop_index('ix_sessions_agent_type', table_name='sessions')

    # Drop tables (in reverse order due to foreign keys)
    op.drop_table('metric_buckets')
    op.drop_table('spec_runs')
    op.drop_table('events')
    op.drop_table('sessions')

    # Drop ENUM types
    sa.ENUM(name='spec_run_status').drop(op.get_bind(), checkfirst=True)
    sa.ENUM(name='agent_type').drop(op.get_bind(), checkfirst=True)
    sa.ENUM(name='session_status').drop(op.get_bind(), checkfirst=True)

    # Note: uuid-ossp extension is left in place
