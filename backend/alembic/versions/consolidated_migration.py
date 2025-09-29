"""Consolidated migration - Add user columns and SDR lead system

Revision ID: consolidated_migration
Revises: 850726fb7fce
Create Date: 2025-09-23 14:16:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'consolidated_migration'
down_revision: Union[str, None] = '850726fb7fce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create lead_profiles table
    op.create_table('lead_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('interests', sa.Text(), nullable=True),
        sa.Column('regions', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_groups', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_profiles_id'), 'lead_profiles', ['id'], unique=False)
    op.create_index('ix_lead_profiles_user_id', 'lead_profiles', ['user_id'], unique=False)
    op.create_index('ix_lead_profiles_keywords', 'lead_profiles', ['keywords'], unique=False)

    # Create leads table
    op.create_table('leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lead_profile_id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=50), nullable=True),
        sa.Column('telegram_username', sa.String(length=100), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('profile_match_keywords', sa.Text(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('conversation_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('status', sa.String(length=20), nullable=True, default='discovered'),
        sa.Column('last_contacted_at', sa.DateTime(), nullable=True),
        sa.Column('last_reply_at', sa.DateTime(), nullable=True),
        sa.Column('source_group', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lead_profile_id'], ['lead_profiles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    op.create_index('ix_leads_user_id', 'leads', ['user_id'], unique=False)
    op.create_index('ix_leads_telegram_user_id', 'leads', ['telegram_user_id'], unique=False)
    op.create_index('ix_leads_relevance_score', 'leads', ['relevance_score'], unique=False)
    op.create_index('ix_leads_status', 'leads', ['status'], unique=False)

    # Create lead_conversations table
    op.create_table('lead_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.String(length=50), nullable=True),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('message_content', sa.Text(), nullable=True),
        sa.Column('ai_generated', sa.Boolean(), nullable=True, default=False),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('intent_detected', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_conversations_id'), 'lead_conversations', ['id'], unique=False)
    op.create_index('ix_lead_conversations_lead_id', 'lead_conversations', ['lead_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_index('ix_lead_conversations_lead_id', table_name='lead_conversations')
    op.drop_index(op.f('ix_lead_conversations_id'), table_name='lead_conversations')
    op.drop_table('lead_conversations')
    
    op.drop_index('ix_leads_status', table_name='leads')
    op.drop_index('ix_leads_relevance_score', table_name='leads')
    op.drop_index('ix_leads_telegram_user_id', table_name='leads')
    op.drop_index('ix_leads_user_id', table_name='leads')
    op.drop_index(op.f('ix_leads_id'), table_name='leads')
    op.drop_table('leads')
    
    op.drop_index('ix_lead_profiles_keywords', table_name='lead_profiles')
    op.drop_index('ix_lead_profiles_user_id', table_name='lead_profiles')
    op.drop_index(op.f('ix_lead_profiles_id'), table_name='lead_profiles')
    op.drop_table('lead_profiles')