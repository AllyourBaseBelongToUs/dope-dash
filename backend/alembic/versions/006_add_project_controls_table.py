"""Add project controls table for tracking project control actions.

Revision ID: 006_add_project_controls_table
Revises: 005_add_projects_table
Create Date: 2026-01-30

This migration creates the project_controls table for tracking all control
actions taken on projects (pause, resume, skip, stop, retry, restart).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '006_add_project_controls_table'
down_revision: Union[str, None] = '005_add_projects_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to create project_controls table with indexes."""
    # Create project_control_action ENUM type
    project_control_action_enum = sa.ENUM(
        'pause', 'resume', 'skip', 'stop', 'retry', 'restart',
        name='project_control_action',
        create_type=True,
    )
    project_control_action_enum.create(op.get_bind(), checkfirst=True)

    # Create project_control_status ENUM type
    project_control_status_enum = sa.ENUM(
        'pending', 'acknowledged', 'completed', 'failed', 'timeout',
        name='project_control_status',
        create_type=True,
    )
    project_control_status_enum.create(op.get_bind(), checkfirst=True)

    # Create project_controls table
    op.create_table(
        'project_controls',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('action', project_control_action_enum, nullable=False),
        sa.Column('status', project_control_status_enum, nullable=False, server_default='pending'),
        sa.Column('initiated_by', sa.String(length=255), nullable=False, server_default='user'),
        sa.Column('agents_affected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_project_controls_project_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for project_controls
    op.create_index('ix_project_controls_project_id', 'project_controls', ['project_id'])
    op.create_index('ix_project_controls_action', 'project_controls', ['action'])
    op.create_index('ix_project_controls_status', 'project_controls', ['status'])

    # Create updated_at trigger for project_controls table
    op.execute('''
        CREATE TRIGGER update_project_controls_updated_at
        BEFORE UPDATE ON project_controls
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')


def downgrade() -> None:
    """Downgrade to remove project_controls table."""
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_project_controls_updated_at ON project_controls')

    # Drop indexes
    op.drop_index('ix_project_controls_status', table_name='project_controls')
    op.drop_index('ix_project_controls_action', table_name='project_controls')
    op.drop_index('ix_project_controls_project_id', table_name='project_controls')

    # Drop table
    op.drop_table('project_controls')

    # Drop ENUM types
    sa.ENUM(name='project_control_status').drop(op.get_bind(), checkfirst=True)
    sa.ENUM(name='project_control_action').drop(op.get_bind(), checkfirst=True)
