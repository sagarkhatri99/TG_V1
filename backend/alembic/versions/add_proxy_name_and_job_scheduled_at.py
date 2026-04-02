"""Add proxy name and job scheduled_at columns

Revision ID: add_proxy_name_and_job_scheduled_at
Revises: 
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'add_proxy_name_sched'
down_revision = 'fix_proxy_nullable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add name column to proxies table
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(100), nullable=True))

    # Add scheduled_at column to jobs table
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.add_column(sa.Column('scheduled_at', sa.DateTime, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.drop_column('name')

    with op.batch_alter_table('jobs') as batch_op:
        batch_op.drop_column('scheduled_at')
