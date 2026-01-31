"""Add soft delete columns to events and sessions tables.

Revision ID: 004_add_soft_delete_columns
Revises: 003_add_agent_metadata_columns
Create Date: 2026-01-30

This migration adds soft delete functionality:
- deleted_at column to events table
- deleted_at column to sessions table

Soft delete allows data to be marked for deletion without immediately
removing it, providing a grace period for recovery.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_soft_delete_columns'
down_revision: Union[str, None] = '003_add_agent_metadata_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add soft delete columns."""
    # Add deleted_at column to events table
    op.add_column(
        'events',
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.create_index('ix_events_deleted_at', 'events', ['deleted_at'])

    # Add deleted_at column to sessions table
    op.add_column(
        'sessions',
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.create_index('ix_sessions_deleted_at', 'sessions', ['deleted_at'])


def downgrade() -> None:
    """Downgrade to remove soft delete columns."""
    # Drop indexes first
    op.drop_index('ix_sessions_deleted_at', table_name='sessions')
    op.drop_index('ix_events_deleted_at', table_name='events')

    # Drop columns
    op.drop_column('sessions', 'deleted_at')
    op.drop_column('events', 'deleted_at')
