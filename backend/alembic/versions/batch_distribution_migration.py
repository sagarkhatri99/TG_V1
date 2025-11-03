"""Add batch distribution fields for distributed Mass DM

Revision ID: batch_distribution
Revises: job_tracking_fields
Create Date: 2025-11-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'batch_distribution'
down_revision: Union[str, None] = 'job_tracking_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add batch distribution fields to jobs table
    op.add_column('jobs', sa.Column('parent_job_id', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('batch_number', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('total_batches', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('batch_user_ids', sa.Text(), nullable=True))
    
    # Create foreign key for parent_job_id
    op.create_foreign_key(
        'fk_jobs_parent_job_id',
        'jobs', 'jobs',
        ['parent_job_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_jobs_parent_job_id', 'jobs', type_='foreignkey')
    
    # Drop columns
    op.drop_column('jobs', 'batch_user_ids')
    op.drop_column('jobs', 'total_batches')
    op.drop_column('jobs', 'batch_number')
    op.drop_column('jobs', 'parent_job_id')
