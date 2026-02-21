"""Add request queue table for throttling and delayed request processing.

Revision ID: 012_add_request_queue_table
Revises: 011_add_rate_limit_events_table
Create Date: 2026-02-19

This migration:
1. Creates request_queue table for storing queued API requests
2. Adds priority system (high, medium, low) with numeric weights
3. Implements queue status tracking (pending, processing, completed, failed, cancelled)
4. Supports retry counting with exponential backoff
5. Enables queue persistence across restarts
6. Creates indexes for efficient queue queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import enum


# revision identifiers, used by Alembic.
revision: str = '012_add_request_queue_table'
down_revision: Union[str, None] = '011_add_rate_limit_events_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add request queue table."""

    # Step 1: Create queue_priority ENUM type
    # Higher numeric values = higher priority (high=3, medium=2, low=1)
    queue_priority_enum = postgresql.ENUM(
        'low', 'medium', 'high',
        name='queue_priority',
        create_type=True,
    )
    queue_priority_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: Create queue_status ENUM type
    queue_status_enum = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed', 'cancelled',
        name='queue_status',
        create_type=True,
    )
    queue_status_enum.create(op.get_bind(), checkfirst=True)

    # Step 3: Create request_queue table
    op.create_table(
        'request_queue',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=False, comment='API provider for this request'),
        sa.Column('project_id', sa.UUID(), nullable=True, comment='Associated project (null for global requests)'),
        sa.Column('session_id', sa.UUID(), nullable=True, comment='Associated session if applicable'),
        sa.Column('endpoint', sa.Text(), nullable=False, comment='Target endpoint URL'),
        sa.Column('method', sa.Text(), nullable=False, server_default='POST', comment='HTTP method'),
        sa.Column('payload', sa.JSON(), nullable=False, server_default='{}', comment='Request body/payload'),
        sa.Column('headers', sa.JSON(), nullable=False, server_default='{}', comment='Request headers'),
        sa.Column('priority', queue_priority_enum, nullable=False, server_default='medium', comment='Queue priority (high, medium, low)'),
        sa.Column('status', queue_status_enum, nullable=False, server_default='pending', comment='Queue status'),
        sa.Column('scheduled_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='When to process this request (null = immediately)'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0', comment='Number of retry attempts'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3', comment='Maximum retry attempts'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='Last error message if failed'),
        sa.Column('error_details', sa.JSON(), nullable=False, server_default='{}', comment='Detailed error information'),
        sa.Column('processing_started_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='When processing started'),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='When successfully completed'),
        sa.Column('failed_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='When failed'),
        sa.Column('cancelled_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='When cancelled'),
        sa.Column('meta', sa.JSON(), nullable=False, server_default='{}', comment='Additional metadata'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='fk_request_queue_provider_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_request_queue_project_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name='fk_request_queue_session_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Step 4: Create indexes for efficient queue queries
    # Primary query index for pending requests ordered by priority and scheduled time
    op.create_index(
        'ix_request_queue_priority_status_scheduled',
        'request_queue',
        ['status', 'scheduled_at', 'priority'],
        # Uses PostgreSQL partial index for pending items only
        postgresql_where=sa.text("status = 'pending'")
    )

    op.create_index('ix_request_queue_provider_id', 'request_queue', ['provider_id'])
    op.create_index('ix_request_queue_project_id', 'request_queue', ['project_id'])
    op.create_index('ix_request_queue_session_id', 'request_queue', ['session_id'])
    op.create_index('ix_request_queue_status', 'request_queue', ['status'])
    op.create_index('ix_request_queue_scheduled_at', 'request_queue', ['scheduled_at'])
    op.create_index('ix_request_queue_created_at', 'request_queue', ['created_at'])

    # Composite index for project-specific queue queries
    op.create_index(
        'ix_request_queue_project_status',
        'request_queue',
        ['project_id', 'status']
    )

    # Composite index for provider queue depth monitoring
    op.create_index(
        'ix_request_queue_provider_status',
        'request_queue',
        ['provider_id', 'status']
    )

    # Step 5: Create updated_at trigger
    op.execute('''
        CREATE TRIGGER update_request_queue_updated_at
        BEFORE UPDATE ON request_queue
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    # Step 6: Create function for priority ordering
    # High priority = weight 3, Medium = 2, Low = 1
    op.execute('''
        CREATE OR REPLACE FUNCTION queue_priority_weight(priority TEXT)
        RETURNS INTEGER AS $$
        BEGIN
            RETURN CASE priority
                WHEN 'high' THEN 3
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 1
                ELSE 0
            END;
        END;
        LANGUAGE plpgsql IMMUTABLE;
    ''')

    # Step 7: Create helper function to get next queued request
    op.execute('''
        CREATE OR REPLACE FUNCTION get_next_queued_request(p_provider_id UUID DEFAULT NULL)
        RETURNS UUID AS $$
        DECLARE
            v_request_id UUID;
        BEGIN
            SELECT id INTO v_request_id
            FROM request_queue
            WHERE status = 'pending'
              AND (scheduled_at IS NULL OR scheduled_at <= NOW())
              AND (p_provider_id IS NULL OR provider_id = p_provider_id)
            ORDER BY queue_priority_weight(priority) DESC, created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED;

            RETURN v_request_id;
        END;
        LANGUAGE plpgsql;
    ''')


def downgrade() -> None:
    """Downgrade to remove request queue table."""

    # Drop helper functions
    op.execute('DROP FUNCTION IF EXISTS get_next_queued_request(UUID)')
    op.execute('DROP FUNCTION IF EXISTS queue_priority_weight(TEXT)')

    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_request_queue_updated_at ON request_queue')

    # Drop indexes
    op.drop_index('ix_request_queue_provider_status', table_name='request_queue')
    op.drop_index('ix_request_queue_project_status', table_name='request_queue')
    op.drop_index('ix_request_queue_created_at', table_name='request_queue')
    op.drop_index('ix_request_queue_scheduled_at', table_name='request_queue')
    op.drop_index('ix_request_queue_status', table_name='request_queue')
    op.drop_index('ix_request_queue_session_id', table_name='request_queue')
    op.drop_index('ix_request_queue_project_id', table_name='request_queue')
    op.drop_index('ix_request_queue_provider_id', table_name='request_queue')
    op.drop_index('ix_request_queue_priority_status_scheduled', table_name='request_queue')

    # Drop table
    op.drop_table('request_queue')

    # Drop ENUM types
    postgresql.ENUM(name='queue_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='queue_priority').drop(op.get_bind(), checkfirst=True)
