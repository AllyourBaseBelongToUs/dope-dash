"""Add rate limit events table for 429 error tracking and exponential backoff.

Revision ID: 011_add_rate_limit_events_table
Revises: 010_add_quota_tracking_tables
Create Date: 2026-01-31

This migration:
1. Creates rate_limit_events table for tracking 429 errors
2. Adds retry tracking with attempt count and status
3. Stores response headers for Retry-After parsing
4. Creates indexes for efficient rate limit queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '011_add_rate_limit_events_table'
down_revision: Union[str, None] = '010_add_quota_tracking_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add rate limit events table."""

    # Step 1: Create rate_limit_event_status ENUM type
    rate_limit_status_enum = sa.ENUM(
        'detected', 'retrying', 'resolved', 'failed',
        name='rate_limit_event_status',
        create_type=True,
    )
    rate_limit_status_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: Create rate_limit_events table
    op.create_table(
        'rate_limit_events',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True, comment='Null for global events, set for project-specific'),
        sa.Column('session_id', sa.UUID(), nullable=True, comment='Associated session if applicable'),
        sa.Column('http_status_code', sa.Integer(), nullable=False, comment='HTTP status code (429 for rate limit)'),
        sa.Column('request_endpoint', sa.Text(), nullable=False, comment='The endpoint that was being requested'),
        sa.Column('request_method', sa.Text(), nullable=False, server_default='POST', comment='HTTP method used'),
        sa.Column('response_headers', sa.JSON(), nullable=False, server_default='{}', comment='Full response headers including Retry-After'),
        sa.Column('retry_after_seconds', sa.Integer(), nullable=True, comment='Retry-After header value in seconds'),
        sa.Column('retry_after_date', sa.TIMESTAMP(timezone=True), nullable=True, comment='Retry-After as HTTP-date'),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1', comment='Current retry attempt (1-based)'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='5', comment='Maximum retry attempts'),
        sa.Column('status', rate_limit_status_enum, nullable=False, server_default='detected'),
        sa.Column('calculated_backoff_seconds', sa.Integer(), nullable=True, comment='Exponential backoff delay calculated'),
        sa.Column('jitter_seconds', sa.Integer(), nullable=True, comment='Random jitter added to prevent thundering herd'),
        sa.Column('error_details', sa.JSON(), nullable=False, server_default='{}', comment='Error response body or details'),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='When the request succeeded'),
        sa.Column('failed_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='When max retries were exhausted'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('detected_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='fk_rate_limit_events_provider_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_rate_limit_events_project_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name='fk_rate_limit_events_session_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Step 3: Create indexes for rate_limit_events
    op.create_index('ix_rate_limit_events_provider_id', 'rate_limit_events', ['provider_id'])
    op.create_index('ix_rate_limit_events_project_id', 'rate_limit_events', ['project_id'])
    op.create_index('ix_rate_limit_events_session_id', 'rate_limit_events', ['session_id'])
    op.create_index('ix_rate_limit_events_status', 'rate_limit_events', ['status'])
    op.create_index('ix_rate_limit_events_detected_at', 'rate_limit_events', ['detected_at'])
    op.create_index('ix_rate_limit_events_http_status_code', 'rate_limit_events', ['http_status_code'])
    op.create_index('ix_rate_limit_events_provider_detected', 'rate_limit_events', ['provider_id', 'detected_at'])

    # Step 4: Create updated_at trigger
    op.execute('''
        CREATE TRIGGER update_rate_limit_events_updated_at
        BEFORE UPDATE ON rate_limit_events
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')


def downgrade() -> None:
    """Downgrade to remove rate limit events table."""

    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_rate_limit_events_updated_at ON rate_limit_events')

    # Drop indexes
    op.drop_index('ix_rate_limit_events_provider_detected', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_events_http_status_code', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_events_detected_at', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_events_status', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_events_session_id', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_events_project_id', table_name='rate_limit_events')
    op.drop_index('ix_rate_limit_events_provider_id', table_name='rate_limit_events')

    # Drop table
    op.drop_table('rate_limit_events')

    # Drop ENUM type
    sa.ENUM(name='rate_limit_event_status').drop(op.get_bind(), checkfirst=True)
