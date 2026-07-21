"""HU-07: permiso members.gestionar_usuarios

Revision ID: f3c77f7db862
Revises: 8a0c59bb9387
Create Date: 2026-07-10 16:56:18.826254

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3c77f7db862'
down_revision = '8a0c59bb9387'
branch_labels = None
depends_on = None


permisos_table = sa.table(
    "permisos",
    sa.column("codigo", sa.String),
    sa.column("descripcion", sa.String),
)

_CATALOGO_NUEVO = [
    {
        "codigo": "members.gestionar_usuarios",
        "descripcion": (
            "CRUD básico de usuarios: crear, listar, ver, editar y eliminar "
            "(POST/GET/PUT/DELETE /usuarios). Independiente de "
            "members.asignar_rol_empleado, que controla a qué rol se puede "
            "crear/ascender, no si se puede gestionar usuarios en general."
        ),
    },
]


def upgrade() -> None:
    op.bulk_insert(permisos_table, _CATALOGO_NUEVO)


def downgrade() -> None:
    op.execute("DELETE FROM permisos WHERE codigo = 'members.gestionar_usuarios'")
