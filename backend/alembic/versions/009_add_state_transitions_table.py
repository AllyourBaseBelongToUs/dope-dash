"""Add state_transitions table for project state machine audit trail.

Revision ID: 009_add_state_transitions_table
Revises: 008_add_agent_pool_table
Create Date: 2026-01-31

This migration:
1. Adds 'queued' and 'cancelled' to project_status ENUM
2. Creates state_transitions table for tracking all state changes
3. Adds indexes for efficient state history queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '009_add_state_transitions_table'
down_revision: Union[str, None] = '008_add_agent_pool_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add state_transitions table and extend project_status enum."""

    # Step 1: Add 'queued' and 'cancelled' to project_status ENUM
    # PostgreSQL requires adding new values after the type is altered
    op.execute("ALTER TYPE project_status ADD VALUE 'queued'")
    op.execute("ALTER TYPE project_status ADD VALUE 'cancelled'")

    # Step 2: Create state_transition_source ENUM type
    state_transition_source_enum = sa.ENUM(
        'user', 'system', 'api', 'automation', 'timeout',
        name='state_transition_source',
        create_type=True,
    )
    state_transition_source_enum.create(op.get_bind(), checkfirst=True)

    # Step 3: Create state_transitions table
    op.create_table(
        'state_transitions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('from_state', sa.Enum('idle', 'running', 'paused', 'error', 'completed', 'queued', 'cancelled', name='project_status', create_type=False), nullable=True),
        sa.Column('to_state', sa.Enum('idle', 'running', 'paused', 'error', 'completed', 'queued', 'cancelled', name='project_status', create_type=False), nullable=False),
        sa.Column('transition_reason', sa.Text(), nullable=True),
        sa.Column('source', state_transition_source_enum, nullable=False, server_default='user'),
        sa.Column('initiated_by', sa.String(length=255), nullable=False, server_default='system'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_state_transitions_project_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Step 4: Create indexes for state_transitions
    op.create_index('ix_state_transitions_project_id', 'state_transitions', ['project_id'])
    op.create_index('ix_state_transitions_from_state', 'state_transitions', ['from_state'])
    op.create_index('ix_state_transitions_to_state', 'state_transitions', ['to_state'])
    op.create_index('ix_state_transitions_created_at', 'state_transitions', ['created_at'])
    op.create_index('ix_state_transitions_source', 'state_transitions', ['source'])
    op.create_index('ix_state_transitions_project_created', 'state_transitions', ['project_id', 'created_at'])


def downgrade() -> None:
    """Downgrade to remove state_transitions table and revert project_status enum."""

    # Drop indexes
    op.drop_index('ix_state_transitions_project_created', table_name='state_transitions')
    op.drop_index('ix_state_transitions_source', table_name='state_transitions')
    op.drop_index('ix_state_transitions_created_at', table_name='state_transitions')
    op.drop_index('ix_state_transitions_to_state', table_name='state_transitions')
    op.drop_index('ix_state_transitions_from_state', table_name='state_transitions')
    op.drop_index('ix_state_transitions_project_id', table_name='state_transitions')

    # Drop table
    op.drop_table('state_transitions')

    # Drop ENUM type
    sa.ENUM(name='state_transition_source').drop(op.get_bind(), checkfirst=True)

    # Note: We cannot remove enum values from PostgreSQL
    # The 'queued' and 'cancelled' values will remain in the project_status enum
    # but will not be used if downgraded
