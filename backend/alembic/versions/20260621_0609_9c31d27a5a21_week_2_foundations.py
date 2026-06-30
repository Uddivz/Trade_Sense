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
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.add_column(sa.Column('external_trade_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('broker', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('fees', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint('uix_portfolio_external_trade_id', ['portfolio_id', 'external_trade_id'])

    # holdings
    with op.batch_alter_table('holdings') as batch_op:
        batch_op.alter_column('avg_cost_basis', new_column_name='average_cost')
        batch_op.alter_column('current_price', new_column_name='market_price')
        batch_op.alter_column('current_value', new_column_name='market_value')
        batch_op.alter_column('last_updated_at', new_column_name='updated_at')
        batch_op.add_column(sa.Column('realized_pnl', sa.Numeric(precision=20, scale=4), nullable=False, server_default='0'))
        batch_op.create_unique_constraint('uix_portfolio_symbol', ['portfolio_id', 'symbol'])


def downgrade() -> None:
    # holdings
    with op.batch_alter_table('holdings') as batch_op:
        batch_op.drop_constraint('uix_portfolio_symbol', type_='unique')
        batch_op.drop_column('realized_pnl')
        batch_op.alter_column('updated_at', new_column_name='last_updated_at')
        batch_op.alter_column('market_value', new_column_name='current_value')
        batch_op.alter_column('market_price', new_column_name='current_price')
        batch_op.alter_column('average_cost', new_column_name='avg_cost_basis')

    # transactions
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.drop_constraint('uix_portfolio_external_trade_id', type_='unique')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('fees')
        batch_op.drop_column('broker')
        batch_op.drop_column('external_trade_id')
