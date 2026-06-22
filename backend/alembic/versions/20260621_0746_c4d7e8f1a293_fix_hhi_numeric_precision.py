"""fix_hhi_numeric_precision

Revision ID: c4d7e8f1a293
Revises: 9c31d27a5a21
Create Date: 2026-06-21 07:45:00.000000+00:00

BUG-03 FIX: The hhi column in behavioral_metrics was defined as Numeric(6,5),
which allows a maximum value of 9.99999.  HHI is bounded 0-10,000, so any
portfolio with even two holdings would cause a DataError overflow on insert.
Changed to Numeric(10, 4) to support the full 0-10,000 range.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d7e8f1a293'
down_revision: Union[str, None] = '9c31d27a5a21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alter hhi column from Numeric(6, 5) to Numeric(10, 4)
    # This is safe: widening precision never truncates existing data.
    op.alter_column(
        'behavioral_metrics',
        'hhi',
        type_=sa.Numeric(precision=10, scale=4),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert to original (incorrect) definition — existing rows with hhi > 9
    # will be truncated/errored by the DB on downgrade. Use with caution.
    op.alter_column(
        'behavioral_metrics',
        'hhi',
        type_=sa.Numeric(precision=6, scale=5),
        existing_nullable=True,
    )
