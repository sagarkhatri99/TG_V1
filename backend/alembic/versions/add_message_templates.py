"""Add message_templates table

Revision ID: add_message_templates
Revises: consolidated_migration
Create Date: 2025-10-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_message_templates'
down_revision: Union[str, None] = 'consolidated_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create message_templates table
    op.create_table('message_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True, default="Custom"),
        sa.Column('spam_risk_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_templates_id'), 'message_templates', ['id'], unique=False)
    op.create_index('ix_message_templates_user_id', 'message_templates', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_message_templates_user_id', table_name='message_templates')
    op.drop_index(op.f('ix_message_templates_id'), table_name='message_templates')
    op.drop_table('message_templates')
