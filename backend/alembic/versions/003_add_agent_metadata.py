"""Add agent metadata columns to sessions table.

Revision ID: 003_add_agent_metadata
Revises: 002_add_multi_agent_types
Create Date: 2026-01-30

This migration adds agent runtime metadata to the sessions table:
- pid: Process ID of the agent
- working_dir: Working directory where agent is running
- command: Full command line used to start the agent
- last_heartbeat: Timestamp of last agent heartbeat (for liveness detection)
- tmux_session: Tmux session name (if agent is running in tmux)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_agent_metadata'
down_revision: Union[str, None] = '002_add_multi_agent_types'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add agent metadata columns."""
    # Add new columns to sessions table
    op.add_column(
        'sessions',
        sa.Column('pid', sa.Integer(), nullable=True),
    )
    op.add_column(
        'sessions',
        sa.Column('working_dir', sa.Text(), nullable=True),
    )
    op.add_column(
        'sessions',
        sa.Column('command', sa.Text(), nullable=True),
    )
    op.add_column(
        'sessions',
        sa.Column('last_heartbeat', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        'sessions',
        sa.Column('tmux_session', sa.Text(), nullable=True),
    )

    # Create indexes for common queries
    op.create_index(
        'ix_sessions_pid',
        'sessions',
        ['pid'],
    )
    op.create_index(
        'ix_sessions_tmux_session',
        'sessions',
        ['tmux_session'],
    )
    op.create_index(
        'ix_sessions_last_heartbeat',
        'sessions',
        ['last_heartbeat'],
    )


def downgrade() -> None:
    """Downgrade to remove agent metadata columns."""
    # Drop indexes
    op.drop_index('ix_sessions_last_heartbeat', table_name='sessions')
    op.drop_index('ix_sessions_tmux_session', table_name='sessions')
    op.drop_index('ix_sessions_pid', table_name='sessions')

    # Drop columns
    op.drop_column('sessions', 'tmux_session')
    op.drop_column('sessions', 'last_heartbeat')
    op.drop_column('sessions', 'command')
    op.drop_column('sessions', 'working_dir')
    op.drop_column('sessions', 'pid')
