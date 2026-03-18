"""backlog_03b_ev_zones

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ev_zones',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('order_id', sa.String(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('klic_upload_id', sa.String(), sa.ForeignKey('klic_uploads.id'), nullable=False),
        sa.Column('beheerder', sa.String(), nullable=True),
        sa.Column('geometrie_wkt', sa.Text(), nullable=False),
        sa.Column('netwerk_href', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('ev_zones')
