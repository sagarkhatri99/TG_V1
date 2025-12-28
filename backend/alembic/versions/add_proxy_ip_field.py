"""add_ip_address_to_proxies

Revision ID: add_proxy_ip_field
Revises: batch_distribution_migration
Create Date: 2025-12-12 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_proxy_ip_field'
down_revision: Union[str, None] = 'batch_distribution'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ip_address column to proxies table
    op.add_column('proxies', sa.Column('ip_address', sa.String(length=45), nullable=True))


def downgrade() -> None:
    # Remove ip_address column from proxies table
    op.drop_column('proxies', 'ip_address')
