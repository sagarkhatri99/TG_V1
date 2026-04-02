"""Merge multiple heads

Revision ID: merge_heads_20260326
Revises: reconcile_schema_2026, add_proxy_name_sched
Create Date: 2026-03-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_heads_20260326'
down_revision: Union[str, Sequence[str], None] = ('reconcile_schema_2026', 'add_proxy_name_sched')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
