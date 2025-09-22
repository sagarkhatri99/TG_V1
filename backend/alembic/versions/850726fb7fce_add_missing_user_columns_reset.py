"""add missing user columns (reset)

Revision ID: 850726fb7fce
Revises: 0465f20dd92f
Create Date: 2025-09-22 06:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '850726fb7fce'
down_revision: Union[str, None] = '0465f20dd92f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Added columns for User plan features
    op.add_column('users', sa.Column('billing_cycle', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('trial_end_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('jobs_created_this_month', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('job_counter_last_reset', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'job_counter_last_reset')
    op.drop_column('users', 'jobs_created_this_month')
    op.drop_column('users', 'trial_end_date')
    op.drop_column('users', 'billing_cycle')
