"""Add quota tracking tables for API provider quota monitoring.

Revision ID: 010_add_quota_tracking_tables
Revises: 009_add_state_transitions_table
Create Date: 2026-01-31

This migration:
1. Creates providers table for API provider configuration
2. Creates quota_usage table for real-time quota tracking
3. Creates quota_reset_schedule table for reset schedule tracking
4. Creates quota_alerts table for overage notifications
5. Creates indexes for efficient quota queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision: str = '010_add_quota_tracking_tables'
down_revision: Union[str, None] = '009_add_state_transitions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add quota tracking tables."""

    # Step 1: Create provider_type ENUM type
    provider_type_enum = sa.ENUM(
        'claude', 'gemini', 'openai', 'cursor',
        name='provider_type',
        create_type=True,
    )
    provider_type_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: Create quota_reset_type ENUM type
    quota_reset_type_enum = sa.ENUM(
        'daily', 'monthly', 'fixed_date',
        name='quota_reset_type',
        create_type=True,
    )
    quota_reset_type_enum.create(op.get_bind(), checkfirst=True)

    # Step 3: Create quota_alert_type ENUM type
    quota_alert_type_enum = sa.ENUM(
        'warning', 'critical', 'overage',
        name='quota_alert_type',
        create_type=True,
    )
    quota_alert_type_enum.create(op.get_bind(), checkfirst=True)

    # Step 4: Create quota_alert_status ENUM type
    quota_alert_status_enum = sa.ENUM(
        'active', 'acknowledged', 'resolved',
        name='quota_alert_status',
        create_type=True,
    )
    quota_alert_status_enum.create(op.get_bind(), checkfirst=True)

    # Step 5: Create providers table
    op.create_table(
        'providers',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', provider_type_enum, nullable=False, unique=True),
        sa.Column('display_name', sa.Text(), nullable=False),
        sa.Column('api_endpoint', sa.Text(), nullable=True),
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=True, comment='Requests per minute limit'),
        sa.Column('rate_limit_rph', sa.Integer(), nullable=True, comment='Requests per hour limit'),
        sa.Column('rate_limit_tpm', sa.Integer(), nullable=True, comment='Tokens per minute limit'),
        sa.Column('rate_limit_tokens_per_day', sa.Integer(), nullable=True, comment='Tokens per day limit'),
        sa.Column('default_quota_limit', sa.Integer(), nullable=False, server_default='1000', comment='Default requests per period'),
        sa.Column('quota_reset_type', quota_reset_type_enum, nullable=False, server_default='daily'),
        sa.Column('quota_reset_day_of_month', sa.Integer(), nullable=True, comment='Day of month for reset (1-31)'),
        sa.Column('quota_reset_hour', sa.Integer(), nullable=False, server_default='0', comment='Hour of day for reset (0-23)'),
        sa.Column('quota_reset_timezone', sa.Text(), nullable=False, server_default='UTC'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Step 6: Create quota_usage table
    op.create_table(
        'quota_usage',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True, comment='Null for global quota, set for per-project quota'),
        sa.Column('current_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quota_limit', sa.Integer(), nullable=False),
        sa.Column('quota_limit_tokens', sa.Integer(), nullable=True),
        sa.Column('period_start', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('period_end', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_reset_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_request_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('overage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='fk_quota_usage_provider_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_quota_usage_project_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_id', 'project_id', name='uq_quota_usage_provider_project'),
    )

    # Step 7: Create quota_reset_schedule table
    op.create_table(
        'quota_reset_schedule',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('quota_usage_id', sa.UUID(), nullable=False),
        sa.Column('next_reset_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('reset_type', quota_reset_type_enum, nullable=False),
        sa.Column('reset_day_of_month', sa.Integer(), nullable=True),
        sa.Column('reset_hour', sa.Integer(), nullable=False),
        sa.Column('reset_timezone', sa.Text(), nullable=False, server_default='UTC'),
        sa.Column('last_reset_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['quota_usage_id'], ['quota_usage.id'], name='fk_quota_reset_schedule_quota_usage_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Step 8: Create quota_alerts table
    op.create_table(
        'quota_alerts',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('quota_usage_id', sa.UUID(), nullable=False),
        sa.Column('alert_type', quota_alert_type_enum, nullable=False),
        sa.Column('status', quota_alert_status_enum, nullable=False, server_default='active'),
        sa.Column('threshold_percent', sa.Integer(), nullable=False, comment='Threshold that triggered the alert'),
        sa.Column('current_usage', sa.Integer(), nullable=False),
        sa.Column('quota_limit', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('acknowledged_by', sa.Text(), nullable=True),
        sa.Column('acknowledged_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['quota_usage_id'], ['quota_usage.id'], name='fk_quota_alerts_quota_usage_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Step 9: Create indexes for providers
    op.create_index('ix_providers_name', 'providers', ['name'], unique=True)
    op.create_index('ix_providers_is_active', 'providers', ['is_active'])

    # Step 10: Create indexes for quota_usage
    op.create_index('ix_quota_usage_provider_id', 'quota_usage', ['provider_id'])
    op.create_index('ix_quota_usage_project_id', 'quota_usage', ['project_id'])
    op.create_index('ix_quota_usage_period_end', 'quota_usage', ['period_end'])
    op.create_index('ix_quota_usage_provider_project', 'quota_usage', ['provider_id', 'project_id'], unique=True)

    # Step 11: Create indexes for quota_reset_schedule
    op.create_index('ix_quota_reset_schedule_quota_usage_id', 'quota_reset_schedule', ['quota_usage_id'])
    op.create_index('ix_quota_reset_schedule_next_reset_at', 'quota_reset_schedule', ['next_reset_at'])
    op.create_index('ix_quota_reset_schedule_is_active', 'quota_reset_schedule', ['is_active'])

    # Step 12: Create indexes for quota_alerts
    op.create_index('ix_quota_alerts_quota_usage_id', 'quota_alerts', ['quota_usage_id'])
    op.create_index('ix_quota_alerts_alert_type', 'quota_alerts', ['alert_type'])
    op.create_index('ix_quota_alerts_status', 'quota_alerts', ['status'])
    op.create_index('ix_quota_alerts_created_at', 'quota_alerts', ['created_at'])

    # Step 13: Create updated_at triggers
    op.execute('''
        CREATE TRIGGER update_providers_updated_at
        BEFORE UPDATE ON providers
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    op.execute('''
        CREATE TRIGGER update_quota_usage_updated_at
        BEFORE UPDATE ON quota_usage
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    op.execute('''
        CREATE TRIGGER update_quota_reset_schedule_updated_at
        BEFORE UPDATE ON quota_reset_schedule
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    op.execute('''
        CREATE TRIGGER update_quota_alerts_updated_at
        BEFORE UPDATE ON quota_alerts
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    # Step 14: Insert default providers
    op.execute('''
        INSERT INTO providers (name, display_name, api_endpoint, rate_limit_rpm, rate_limit_tpm, rate_limit_tokens_per_day, default_quota_limit, quota_reset_type, quota_reset_hour)
        VALUES
            ('claude', 'Claude (Anthropic)', 'https://api.anthropic.com', 50, 100000, 5000000, 1000, 'daily', 0),
            ('gemini', 'Gemini (Google)', 'https://generativelanguage.googleapis.com', 60, 120000, 15000000, 1500, 'daily', 0),
            ('openai', 'OpenAI (GPT)', 'https://api.openai.com', 3500, 90000, 200000000, 10000, 'daily', 0),
            ('cursor', 'Cursor AI', 'https://api.cursor.sh', 40, 80000, 4000000, 800, 'daily', 0)
        ON CONFLICT (name) DO NOTHING;
    ''')


def downgrade() -> None:
    """Downgrade to remove quota tracking tables."""

    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_quota_alerts_updated_at ON quota_alerts')
    op.execute('DROP TRIGGER IF EXISTS update_quota_reset_schedule_updated_at ON quota_reset_schedule')
    op.execute('DROP TRIGGER IF EXISTS update_quota_usage_updated_at ON quota_usage')
    op.execute('DROP TRIGGER IF EXISTS update_providers_updated_at ON providers')

    # Drop indexes for quota_alerts
    op.drop_index('ix_quota_alerts_created_at', table_name='quota_alerts')
    op.drop_index('ix_quota_alerts_status', table_name='quota_alerts')
    op.drop_index('ix_quota_alerts_alert_type', table_name='quota_alerts')
    op.drop_index('ix_quota_alerts_quota_usage_id', table_name='quota_alerts')

    # Drop indexes for quota_reset_schedule
    op.drop_index('ix_quota_reset_schedule_is_active', table_name='quota_reset_schedule')
    op.drop_index('ix_quota_reset_schedule_next_reset_at', table_name='quota_reset_schedule')
    op.drop_index('ix_quota_reset_schedule_quota_usage_id', table_name='quota_reset_schedule')

    # Drop indexes for quota_usage
    op.drop_index('ix_quota_usage_provider_project', table_name='quota_usage')
    op.drop_index('ix_quota_usage_period_end', table_name='quota_usage')
    op.drop_index('ix_quota_usage_project_id', table_name='quota_usage')
    op.drop_index('ix_quota_usage_provider_id', table_name='quota_usage')

    # Drop indexes for providers
    op.drop_index('ix_providers_is_active', table_name='providers')
    op.drop_index('ix_providers_name', table_name='providers')

    # Drop tables
    op.drop_table('quota_alerts')
    op.drop_table('quota_reset_schedule')
    op.drop_table('quota_usage')
    op.drop_table('providers')

    # Drop ENUM types
    sa.ENUM(name='quota_alert_status').drop(op.get_bind(), checkfirst=True)
    sa.ENUM(name='quota_alert_type').drop(op.get_bind(), checkfirst=True)
    sa.ENUM(name='quota_reset_type').drop(op.get_bind(), checkfirst=True)
    sa.ENUM(name='provider_type').drop(op.get_bind(), checkfirst=True)
