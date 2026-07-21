"""012-checkin-qr-dinamico: tabla dispositivos_autorizados y permiso checkin.autorizar_dispositivo

Revision ID: c6b7b64b4a95
Revises: 4f2037c9aab7
Create Date: 2026-07-21 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c6b7b64b4a95'
down_revision = '4f2037c9aab7'
branch_labels = None
depends_on = None


permisos_table = sa.table(
    "permisos",
    sa.column("codigo", sa.String),
    sa.column("descripcion", sa.String),
)

_CATALOGO_NUEVO = [
    {
        "codigo": "checkin.autorizar_dispositivo",
        "descripcion": (
            "Autorizar o revocar dispositivos (kioscos) para que puedan usar "
            "/kiosko y generar QR de check-in. Independiente de "
            "checkin.desbloquear_dispositivo, que gestiona el bloqueo por "
            "intentos fallidos (RN-03), no la lista blanca de dispositivos."
        ),
    },
]


def upgrade() -> None:
    op.create_table('dispositivos_autorizados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.String(length=100), nullable=False),
    sa.Column('etiqueta', sa.String(length=100), nullable=True),
    sa.Column('autorizado_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('autorizado_por_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['autorizado_por_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dispositivos_autorizados_device_id'), 'dispositivos_autorizados', ['device_id'], unique=True)
    op.create_index(op.f('ix_dispositivos_autorizados_id'), 'dispositivos_autorizados', ['id'], unique=False)
    op.bulk_insert(permisos_table, _CATALOGO_NUEVO)


def downgrade() -> None:
    op.execute("DELETE FROM permisos WHERE codigo = 'checkin.autorizar_dispositivo'")
    op.drop_index(op.f('ix_dispositivos_autorizados_id'), table_name='dispositivos_autorizados')
    op.drop_index(op.f('ix_dispositivos_autorizados_device_id'), table_name='dispositivos_autorizados')
    op.drop_table('dispositivos_autorizados')
