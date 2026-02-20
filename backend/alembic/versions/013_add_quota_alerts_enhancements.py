"""Add quota alerts enhancements for multi-channel alerting.

Revision ID: 013_add_quota_alerts_enhancements
Revises: 012_add_request_queue_table
Create Date: 2026-02-20

This migration:
1. Adds alert_channels column to quota_alerts for tracking sent channels
2. Adds escalation_count and escalation_at for alert escalation
3. Creates alert_config table for per-provider alert settings
4. Adds cooldown tracking to prevent alert spam
5. Adds last_alert_at to quota_usage for cooldown enforcement
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '013_add_quota_alerts_enhancements'
down_revision: Union[str, None] = '012_add_request_queue_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to add quota alerts enhancements."""

    # Step 1: Create alert_channel ENUM type
    alert_channel_enum = postgresql.ENUM(
        'dashboard', 'desktop', 'audio', 'email',
        name='alert_channel',
        create_type=True,
    )
    alert_channel_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: Add new columns to quota_alerts table
    # Track which channels the alert was sent to
    op.add_column(
        'quota_alerts',
        sa.Column(
            'alert_channels',
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default='{}',
            comment='Channels the alert was sent to (dashboard, desktop, audio)'
        )
    )
    # Track escalation
    op.add_column(
        'quota_alerts',
        sa.Column(
            'escalation_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Number of times alert has been escalated'
        )
    )
    op.add_column(
        'quota_alerts',
        sa.Column(
            'escalation_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='When the last escalation occurred'
        )
    )

    # Step 3: Add last_alert_at to quota_usage for cooldown enforcement
    op.add_column(
        'quota_usage',
        sa.Column(
            'last_alert_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='When the last alert was sent for this usage'
        )
    )

    # Step 4: Create alert_config table for per-provider alert settings
    op.create_table(
        'alert_config',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=True, comment='Provider ID (null for global settings)'),
        sa.Column('project_id', sa.UUID(), nullable=True, comment='Project ID (null for global settings)'),
        sa.Column('warning_threshold', sa.Integer(), nullable=False, server_default='80', comment='Warning threshold percentage'),
        sa.Column('critical_threshold', sa.Integer(), nullable=False, server_default='90', comment='Critical threshold percentage'),
        sa.Column('emergency_threshold', sa.Integer(), nullable=False, server_default='95', comment='Emergency threshold percentage'),
        sa.Column('channels', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}', comment='Enabled alert channels'),
        sa.Column('dashboard_enabled', sa.Boolean(), nullable=False, server_default=True, comment='Show in-dashboard alerts'),
        sa.Column('desktop_enabled', sa.Boolean(), nullable=False, server_default=True, comment='Send desktop notifications'),
        sa.Column('audio_enabled', sa.Boolean(), nullable=False, server_default=True, comment='Play audio alerts at emergency threshold'),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='30', comment='Minutes between alerts for same threshold'),
        sa.Column('escalation_enabled', sa.Boolean(), nullable=False, server_default=True, comment='Enable alert escalation'),
        sa.Column('escalation_minutes', sa.Integer(), nullable=False, server_default='15', comment='Minutes before escalating unacknowledged alert'),
        sa.Column('max_escalations', sa.Integer(), nullable=False, server_default='3', comment='Maximum number of escalations'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='fk_alert_config_provider_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_alert_config_project_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_id', 'project_id', name='uq_alert_config_provider_project'),
    )

    # Step 5: Create indexes for alert_config
    op.create_index('ix_alert_config_provider_id', 'alert_config', ['provider_id'])
    op.create_index('ix_alert_config_project_id', 'alert_config', ['project_id'])
    op.create_index('ix_alert_config_is_active', 'alert_config', ['is_active'])

    # Step 6: Create index for escalation queries
    op.create_index(
        'ix_quota_alerts_escalation',
        'quota_alerts',
        ['status', 'escalation_at', 'escalation_count'],
        postgresql_where=sa.text("status = 'active'")
    )

    # Step 7: Create updated_at triggers
    op.execute('''
        CREATE TRIGGER update_alert_config_updated_at
        BEFORE UPDATE ON alert_config
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')

    # Step 8: Insert default global alert config
    op.execute('''
        INSERT INTO alert_config (
            provider_id, project_id,
            warning_threshold, critical_threshold, emergency_threshold,
            channels, dashboard_enabled, desktop_enabled, audio_enabled,
            cooldown_minutes, escalation_enabled, escalation_minutes, max_escalations,
            is_active
        )
        VALUES (
            NULL, NULL,
            80, 90, 95,
            ARRAY['dashboard', 'desktop', 'audio'], true, true, true,
            30, true, 15, 3,
            true
        )
    ''')

    # Step 9: Create function to check if alert should be sent (cooldown check)
    op.execute('''
        CREATE OR REPLACE FUNCTION should_send_alert(
            p_quota_usage_id UUID,
            p_threshold INTEGER,
            p_cooldown_minutes INTEGER DEFAULT 30
        )
        RETURNS BOOLEAN AS $$
        DECLARE
            v_last_alert_at TIMESTAMP WITH TIME ZONE;
            v_cooldown_interval INTERVAL;
        BEGIN
            -- Get the last alert time for this usage and threshold
            SELECT created_at INTO v_last_alert_at
            FROM quota_alerts
            WHERE quota_usage_id = p_quota_usage_id
              AND threshold_percent >= p_threshold
              AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1;

            -- If no previous alert, allow sending
            IF v_last_alert_at IS NULL THEN
                RETURN true;
            END IF;

            -- Check if cooldown period has elapsed
            v_cooldown_interval := INTERVAL '1 minute' * p_cooldown_minutes;
            RETURN (NOW() - v_last_alert_at) >= v_cooldown_interval;
        END;
        LANGUAGE plpgsql STABLE;
    ''')


def downgrade() -> None:
    """Downgrade to remove quota alerts enhancements."""

    # Drop helper function
    op.execute('DROP FUNCTION IF EXISTS should_send_alert(UUID, INTEGER, INTEGER)')

    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS update_alert_config_updated_at ON alert_config')

    # Drop indexes
    op.drop_index('ix_quota_alerts_escalation', table_name='quota_alerts')
    op.drop_index('ix_alert_config_is_active', table_name='alert_config')
    op.drop_index('ix_alert_config_project_id', table_name='alert_config')
    op.drop_index('ix_alert_config_provider_id', table_name='alert_config')

    # Drop tables
    op.drop_table('alert_config')

    # Drop columns from quota_usage
    op.drop_column('quota_usage', 'last_alert_at')

    # Drop columns from quota_alerts
    op.drop_column('quota_alerts', 'escalation_at')
    op.drop_column('quota_alerts', 'escalation_count')
    op.drop_column('quota_alerts', 'alert_channels')

    # Drop ENUM type
    postgresql.ENUM(name='alert_channel').drop(op.get_bind(), checkfirst=True)
