"""Add multi-agent types: ralph, claude, cursor, terminal.

Revision ID: 002_add_multi_agent_types
Revises: 001
Create Date: 2026-01-30

This migration extends the agent_type enum to support multiple agent types:
- ralph: Ralph Inferno - tmux-based spec execution agent
- claude: Claude Code - CLI-based AI coding assistant
- cursor: Cursor IDE - GUI-based AI code editor
- terminal: Terminal session - raw shell session tracking

Legacy agent types (crawler, analyzer, reporter, tester, custom) are retained
for backward compatibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '002_add_multi_agent_types'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add new agent types to the enum."""
    # Get the current bind
    bind = op.get_bind()

    # In PostgreSQL, we need to:
    # 1. Add new values to the existing enum
    # 2. Update the column type to use the modified enum

    # First, add the new enum values to the existing agent_type enum
    op.execute("""
        ALTER TYPE agent_type
        ADD VALUE IF NOT EXISTS 'ralph';
    """)

    op.execute("""
        ALTER TYPE agent_type
        ADD VALUE IF NOT EXISTS 'claude';
    """)

    op.execute("""
        ALTER TYPE agent_type
        ADD VALUE IF NOT EXISTS 'cursor';
    """)

    op.execute("""
        ALTER TYPE agent_type
        ADD VALUE IF NOT EXISTS 'terminal';
    """)


def downgrade() -> None:
    """Downgrade to remove new agent types.

    Note: PostgreSQL doesn't support removing enum values directly.
    To properly downgrade, you would need to:
    1. Create a new enum without the values
    2. Update the column to use the new enum
    3. Drop the old enum

    For simplicity, this downgrade is a no-op, but the enum values
    will remain in the database.
    """
    # No-op: PostgreSQL doesn't support removing enum values
    # To fully rollback, you would need to recreate the enum
    pass
