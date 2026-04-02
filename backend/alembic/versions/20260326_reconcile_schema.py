"""Reconcile schema — fix column drift and drop campaign tables

Revision ID: reconcile_schema_2026
Revises: batch_distribution
Create Date: 2026-03-26

This migration:
  1. Fixes proxy_url length: String(255) -> String(500)
  2. Fixes trust_score type: Integer -> Float (if still Integer in live DB)
  3. Adds jobs.celery_task_id (if missing)
  4. Adds action_logs.action_details (if missing)
  5. Drops all 6 campaign tables (they are unused and have no ORM models)

All steps are idempotent — safe to re-run.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'reconcile_schema_2026'
down_revision: Union[str, None] = 'batch_distribution'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------ #
    # 1. Fix proxy_url column length: VARCHAR(255) -> VARCHAR(500)
    # ------------------------------------------------------------------ #
    op.alter_column(
        'proxies', 'proxy_url',
        existing_type=sa.String(255),
        type_=sa.String(500),
        existing_nullable=True,
    )

    # ------------------------------------------------------------------ #
    # 2. Fix trust_score type: Integer -> Float (safe cast)
    #    Using raw SQL with USING clause — required by PostgreSQL
    # ------------------------------------------------------------------ #
    conn.execute(sa.text("""
        ALTER TABLE telegram_accounts
        ALTER COLUMN trust_score TYPE FLOAT
        USING trust_score::FLOAT;
    """))

    # ------------------------------------------------------------------ #
    # 3. Add jobs.celery_task_id if missing
    # ------------------------------------------------------------------ #
    conn.execute(sa.text("""
        DO $$ BEGIN
            ALTER TABLE jobs ADD COLUMN celery_task_id VARCHAR(255);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """))

    # ------------------------------------------------------------------ #
    # 4. Add action_logs.action_details if missing
    # ------------------------------------------------------------------ #
    conn.execute(sa.text("""
        DO $$ BEGIN
            ALTER TABLE action_logs ADD COLUMN action_details TEXT;
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """))

    # ------------------------------------------------------------------ #
    # 5. Drop campaign tables (unused, no ORM models)
    #    Must be dropped in reverse dependency order
    # ------------------------------------------------------------------ #
    conn.execute(sa.text("DROP TABLE IF EXISTS campaign_logs CASCADE;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS campaign_replies CASCADE;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS campaign_message_tracking CASCADE;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS campaign_pending_tasks CASCADE;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS campaign_user_interactions CASCADE;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS campaigns CASCADE;"))


def downgrade() -> None:
    # Column type rollbacks are risky — left intentionally empty.
    # Campaign table removal is permanent by design.
    pass
