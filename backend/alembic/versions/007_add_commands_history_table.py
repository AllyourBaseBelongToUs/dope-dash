"""Add commands_history table for tracking custom commands.

Revision ID: 007_add_commands_history_table
Revises: 006_add_project_controls_table
Create Date: 2026-01-30

This migration creates the commands_history table for tracking all custom
commands sent to agents, including command content, results, and metadata.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '007_add_commands_history_table'
down_revision: Union[str, None] = '006_add_project_controls_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to create commands_history table with indexes."""
    # Create command_status ENUM type
    command_status_enum = sa.ENUM(
        'pending', 'sent', 'acknowledged', 'completed', 'failed', 'timeout',
        name='command_status',
        create_type=True,
    )
    command_status_enum.create(op.get_bind(), checkfirst=True)

    # Create commands_history table
    op.create_table(
        'commands_history',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('status', command_status_enum, nullable=False, server_default='pending'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('template_name', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_commands_history_project_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for commands_history
    op.create_index('ix_commands_history_project_id', 'commands_history', ['project_id'])
    op.create_index('ix_commands_history_session_id', 'commands_history', ['session_id'])
    op.create_index('ix_commands_history_status', 'commands_history', ['status'])
    op.create_index('ix_commands_history_is_favorite', 'commands_history', ['is_favorite'])
    op.create_index('ix_commands_history_created_at', 'commands_history', ['created_at'])
    op.create_index('ix_commands_history_command', 'commands_history', ['command'], postgresql_prefix='FULLTEXT', postgresql_ops={'command': 'gin_trgm_ops'})

    # Create updated_at trigger for commands_history table
    op.execute('''
        CREATE TRIGGER update_commands_history_updated_at
        BEFORE UPDATE ON commands_history
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')


def downgrade() -> None:
    """Downgrade to remove commands_history table."""
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_commands_history_updated_at ON commands_history')

    # Drop indexes
    op.drop_index('ix_commands_history_command', table_name='commands_history')
    op.drop_index('ix_commands_history_created_at', table_name='commands_history')
    op.drop_index('ix_commands_history_is_favorite', table_name='commands_history')
    op.drop_index('ix_commands_history_status', table_name='commands_history')
    op.drop_index('ix_commands_history_session_id', table_name='commands_history')
    op.drop_index('ix_commands_history_project_id', table_name='commands_history')

    # Drop table
    op.drop_table('commands_history')

    # Drop ENUM type
    sa.ENUM(name='command_status').drop(op.get_bind(), checkfirst=True)
