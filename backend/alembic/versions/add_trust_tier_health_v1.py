"""Add account_trust_tier and optimize message_logs

Revision ID: add_trust_tier_health_v1
Revises: merge_heads_20260326
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_trust_tier_health_v1'
down_revision = 'merge_heads_20260326'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add account_trust_tier to telegram_accounts
    op.add_column('telegram_accounts', sa.Column('account_trust_tier', sa.String(length=20), server_default='warming', nullable=True))
    
    # 2. Add indexes to message_logs for dashboard/rate-limiter performance
    op.create_index('ix_message_logs_telegram_account_id', 'message_logs', ['telegram_account_id'], unique=False)
    op.create_index('ix_message_logs_job_id', 'message_logs', ['job_id'], unique=False)
    op.create_index('ix_message_logs_target_user_id', 'message_logs', ['target_user_id'], unique=False)
    op.create_index('ix_message_logs_delivery_status', 'message_logs', ['delivery_status'], unique=False)
    op.create_index('ix_message_logs_timestamp', 'message_logs', ['timestamp'], unique=False)
    
    # 3. Add UniqueConstraint to message_logs to prevent duplicate outcomes
    op.create_unique_constraint('uq_job_target', 'message_logs', ['job_id', 'target_user_id'])

def downgrade():
    op.drop_constraint('uq_job_target', 'message_logs', type_='unique')
    op.drop_index('ix_message_logs_timestamp', table_name='message_logs')
    op.drop_index('ix_message_logs_delivery_status', table_name='message_logs')
    op.drop_index('ix_message_logs_target_user_id', table_name='message_logs')
    op.drop_index('ix_message_logs_job_id', table_name='message_logs')
    op.drop_index('ix_message_logs_telegram_account_id', table_name='message_logs')
    op.drop_column('telegram_accounts', 'account_trust_tier')
