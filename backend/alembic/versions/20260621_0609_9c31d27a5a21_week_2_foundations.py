"""week_2_foundations

Revision ID: 9c31d27a5a21
Revises: f288aa2e299e
Create Date: 2026-06-21 06:09:18.312649+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c31d27a5a21'
down_revision: Union[str, None] = 'f288aa2e299e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # transactions
    op.add_column('transactions', sa.Column('external_trade_id', sa.String(length=100), nullable=True))
    op.add_column('transactions', sa.Column('broker', sa.String(length=100), nullable=True))
    op.add_column('transactions', sa.Column('fees', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0'))
    op.add_column('transactions', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint('uix_portfolio_external_trade_id', 'transactions', ['portfolio_id', 'external_trade_id'])

    # holdings
    op.alter_column('holdings', 'avg_cost_basis', new_column_name='average_cost')
    op.alter_column('holdings', 'current_price', new_column_name='market_price')
    op.alter_column('holdings', 'current_value', new_column_name='market_value')
    op.alter_column('holdings', 'last_updated_at', new_column_name='updated_at')
    op.add_column('holdings', sa.Column('realized_pnl', sa.Numeric(precision=20, scale=4), nullable=False, server_default='0'))
    op.create_unique_constraint('uix_portfolio_symbol', 'holdings', ['portfolio_id', 'symbol'])


def downgrade() -> None:
    # holdings
    op.drop_constraint('uix_portfolio_symbol', 'holdings', type_='unique')
    op.drop_column('holdings', 'realized_pnl')
    op.alter_column('holdings', 'updated_at', new_column_name='last_updated_at')
    op.alter_column('holdings', 'market_value', new_column_name='current_value')
    op.alter_column('holdings', 'market_price', new_column_name='current_price')
    op.alter_column('holdings', 'average_cost', new_column_name='avg_cost_basis')

    # transactions
    op.drop_constraint('uix_portfolio_external_trade_id', 'transactions', type_='unique')
    op.drop_column('transactions', 'updated_at')
    op.drop_column('transactions', 'fees')
    op.drop_column('transactions', 'broker')
    op.drop_column('transactions', 'external_trade_id')
