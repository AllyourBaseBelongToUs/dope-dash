"""Add projects table for portfolio view.

Revision ID: 005_add_projects_table
Revises: 004_add_soft_delete_columns
Create Date: 2026-01-30

This migration creates the projects table for the portfolio view:
- projects: Project tracking with status, priority, and progress
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '005_add_projects_table'
down_revision: Union[str, None] = '004_add_soft_delete_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to create projects table with indexes and triggers."""
    # Create project_status ENUM type
    project_status_enum = sa.ENUM(
        'idle', 'running', 'paused', 'error', 'completed',
        name='project_status',
        create_type=True,
    )
    project_status_enum.create(op.get_bind(), checkfirst=True)

    # Create project_priority ENUM type
    project_priority_enum = sa.ENUM(
        'low', 'medium', 'high', 'critical',
        name='project_priority',
        create_type=True,
    )
    project_priority_enum.create(op.get_bind(), checkfirst=True)

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('status', project_status_enum, nullable=False, server_default='idle'),
        sa.Column('priority', project_priority_enum, nullable=False, server_default='medium'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('progress', sa.Float(), nullable=False, server_default=0.0),
        sa.Column('total_specs', sa.Integer(), nullable=False, server_default=0),
        sa.Column('completed_specs', sa.Integer(), nullable=False, server_default=0),
        sa.Column('active_agents', sa.Integer(), nullable=False, server_default=0),
        sa.Column('last_activity_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for projects
    op.create_index('ix_projects_name', 'projects', ['name'], unique=True)
    op.create_index('ix_projects_status', 'projects', ['status'])
    op.create_index('ix_projects_priority', 'projects', ['priority'])
    op.create_index('ix_projects_status_priority', 'projects', ['status', 'priority'])
    op.create_index('ix_projects_last_activity_at', 'projects', ['last_activity_at'])
    op.create_index('ix_projects_deleted_at', 'projects', ['deleted_at'])

    # Create updated_at trigger for projects table
    op.execute('''
        CREATE TRIGGER update_projects_updated_at
        BEFORE UPDATE ON projects
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')


def downgrade() -> None:
    """Downgrade to remove projects table."""
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_projects_updated_at ON projects')

    # Drop indexes
    op.drop_index('ix_projects_deleted_at', table_name='projects')
    op.drop_index('ix_projects_last_activity_at', table_name='projects')
    op.drop_index('ix_projects_status_priority', table_name='projects')
    op.drop_index('ix_projects_priority', table_name='projects')
    op.drop_index('ix_projects_status', table_name='projects')
    op.drop_index('ix_projects_name', table_name='projects')

    # Drop table
    op.drop_table('projects')

    # Drop ENUM types
    sa.ENUM(name='project_priority').drop(op.get_bind(), checkfirst=True)
    sa.ENUM(name='project_status').drop(op.get_bind(), checkfirst=True)
