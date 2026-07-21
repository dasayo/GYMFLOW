"""HU-04: flag cortesia_usada en usuarios

Revision ID: 27f9ec997e70
Revises: b4e1a7c0d9f2
Create Date: 2026-07-20 20:56:25.328174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27f9ec997e70'
down_revision = 'b4e1a7c0d9f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOTA: autogenerate propuso DROP de los índices ix_checkins_fecha_hora
    # (HU-09) e ix_checkins_usuario_dia_activo (HU-01) — ambos creados con SQL
    # crudo, que Alembic no reconoce como metadata ORM. Se quitan a mano,
    # igual que en 002/003/004; esos índices siguen vigentes.
    op.add_column(
        'usuarios',
        sa.Column('cortesia_usada', sa.Boolean(), server_default='false', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('usuarios', 'cortesia_usada')
