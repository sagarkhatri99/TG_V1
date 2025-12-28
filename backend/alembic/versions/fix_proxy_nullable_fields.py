"""fix_proxy_nullable_fields

Revision ID: fix_proxy_nullable
Revises: add_proxy_ip_field
Create Date: 2025-12-12 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_proxy_nullable'
down_revision: Union[str, None] = 'add_proxy_ip_field'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make response_time and last_check nullable
    op.alter_column('proxies', 'response_time', nullable=True)
    op.alter_column('proxies', 'last_check', nullable=True)


def downgrade() -> None:
    # Revert to non-nullable
    op.alter_column('proxies', 'response_time', nullable=False)
    op.alter_column('proxies', 'last_check', nullable=False)
