"""Add agent_pool table for load balancing and capacity tracking.

Revision ID: 008_add_agent_pool_table
Revises: 007_add_commands_history_table
Create Date: 2026-01-31

This migration creates the agent_pool table for managing distributed agents
with load balancing, capacity tracking, and affinity support.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '008_add_agent_pool_table'
down_revision: Union[str, None] = '007_add_commands_history_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to create agent_pool table with indexes."""
    # Create pool_agent_status ENUM type
    pool_agent_status_enum = sa.ENUM(
        'available', 'busy', 'offline', 'maintenance', 'draining',
        name='pool_agent_status',
        create_type=True,
    )
    pool_agent_status_enum.create(op.get_bind(), checkfirst=True)

    # Create agent_pool table
    op.create_table(
        'agent_pool',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=False),
        sa.Column('agent_type', sa.Enum('ralph', 'claude', 'cursor', 'terminal', 'crawler', 'analyzer', 'reporter', 'tester', 'custom', name='agenttype', create_type=False), nullable=False),
        sa.Column('status', pool_agent_status_enum, nullable=False, server_default='available'),
        sa.Column('current_project_id', sa.UUID(), nullable=True),
        sa.Column('current_load', sa.Integer(), nullable=False, server_default=0),
        sa.Column('max_capacity', sa.Integer(), nullable=False, server_default=5),
        sa.Column('capabilities', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column('working_dir', sa.Text(), nullable=True),
        sa.Column('command', sa.Text(), nullable=True),
        sa.Column('tmux_session', sa.String(length=255), nullable=True),
        sa.Column('last_heartbeat', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('total_assigned', sa.Integer(), nullable=False, server_default=0),
        sa.Column('total_completed', sa.Integer(), nullable=False, server_default=0),
        sa.Column('total_failed', sa.Integer(), nullable=False, server_default=0),
        sa.Column('average_task_duration_ms', sa.Integer(), nullable=True),
        sa.Column('affinity_tag', sa.String(length=255), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default=0),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['current_project_id'], ['projects.id'], name='fk_agent_pool_current_project_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for agent_pool
    op.create_index('ix_agent_pool_agent_id', 'agent_pool', ['agent_id'], unique=True)
    op.create_index('ix_agent_pool_status', 'agent_pool', ['status'])
    op.create_index('ix_agent_pool_agent_type', 'agent_pool', ['agent_type'])
    op.create_index('ix_agent_pool_current_project_id', 'agent_pool', ['current_project_id'])
    op.create_index('ix_agent_pool_last_heartbeat', 'agent_pool', ['last_heartbeat'])
    op.create_index('ix_agent_pool_affinity_tag', 'agent_pool', ['affinity_tag'])
    op.create_index('ix_agent_pool_priority', 'agent_pool', ['priority'])
    op.create_index('ix_agent_pool_status_current_load', 'agent_pool', ['status', 'current_load'])

    # Create updated_at trigger for agent_pool table
    op.execute('''
        CREATE TRIGGER update_agent_pool_updated_at
        BEFORE UPDATE ON agent_pool
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')


def downgrade() -> None:
    """Downgrade to remove agent_pool table."""
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_agent_pool_updated_at ON agent_pool')

    # Drop indexes
    op.drop_index('ix_agent_pool_status_current_load', table_name='agent_pool')
    op.drop_index('ix_agent_pool_priority', table_name='agent_pool')
    op.drop_index('ix_agent_pool_affinity_tag', table_name='agent_pool')
    op.drop_index('ix_agent_pool_last_heartbeat', table_name='agent_pool')
    op.drop_index('ix_agent_pool_current_project_id', table_name='agent_pool')
    op.drop_index('ix_agent_pool_agent_type', table_name='agent_pool')
    op.drop_index('ix_agent_pool_status', table_name='agent_pool')
    op.drop_index('ix_agent_pool_agent_id', table_name='agent_pool')

    # Drop table
    op.drop_table('agent_pool')

    # Drop ENUM type
    sa.ENUM(name='pool_agent_status').drop(op.get_bind(), checkfirst=True)
