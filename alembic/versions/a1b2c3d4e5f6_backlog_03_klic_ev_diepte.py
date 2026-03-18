"""backlog_03_klic_ev_diepte

Revision ID: a1b2c3d4e5f6
Revises: d35c9f206327
Create Date: 2026-03-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd35c9f206327'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('klic_leidingen', sa.Column('diepte_bron', sa.String(), nullable=True))
    op.add_column('klic_leidingen', sa.Column('mogelijk_sleufloze', sa.Boolean(), nullable=True))
    op.add_column('klic_leidingen', sa.Column('ev_verplicht', sa.Boolean(), nullable=True))
    op.add_column('klic_leidingen', sa.Column('ev_contactgegevens', sa.String(), nullable=True))
    op.add_column('klic_leidingen', sa.Column('label_tekst', sa.Text(), nullable=True))
    op.add_column('klic_leidingen', sa.Column('toelichting_tekst', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('klic_leidingen', 'toelichting_tekst')
    op.drop_column('klic_leidingen', 'label_tekst')
    op.drop_column('klic_leidingen', 'ev_contactgegevens')
    op.drop_column('klic_leidingen', 'ev_verplicht')
    op.drop_column('klic_leidingen', 'mogelijk_sleufloze')
    op.drop_column('klic_leidingen', 'diepte_bron')
